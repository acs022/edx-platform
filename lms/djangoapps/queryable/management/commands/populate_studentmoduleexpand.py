# ======== Populate StudentModuleExpand  ===============================================================================
#
# Populates the StudentModuleExpand table of the queryable_table model.
#
# For the provided course_id, it will find all rows in the StudentModule table of the courseware model that have
# module_type 'problem' and the grade is not null. Then for any rows that have changed since the last populate or do not
# have a corresponding row, update the attempts value.

import json

from datetime import datetime
from pytz import UTC
from django.core.management.base import BaseCommand

from xmodule.modulestore.django import modulestore

from courseware.models import StudentModule
from queryable.models import QueryableLog
from queryable.models import StudentModuleExpand

class Command(BaseCommand):
    help = "Populates the queryable.StudentModuleExpand table.\n"
    help += "Usage: populate_studentmoduleexpand course_id\n"
    help += "   course_id: course's ID, such as Medicine/HRP258/Statistics_in_Medicine\n"

    def handle(self, *args, **options):
        script_id = "studentmoduleexpand"

        print "args = ", args

        if len(args) > 0:
            course_id = args[0]
        else:
            print self.help
            return

        print "--------------------------------------------------------------------------------"
        print "Populating queryable.StudentModuleExpand table for course {0}".format(course_id)
        print "--------------------------------------------------------------------------------"

        # Grab when we start, to log later
        tstart = datetime.now(UTC)

        # Get when this script was last run for this course
        last_log_run = QueryableLog.objects.filter(script_id__exact=script_id, course_id__exact=course_id)
        
        # Get all the problems that students have submitted an answer to for this course, since the last run
        if len(last_log_run) > 0:
            print "--------------------------------------------------------------------------------"
            print "Last log run", last_log_run[0].created, ". Finding all rows created or modified since then."
            print "--------------------------------------------------------------------------------"
            smRows = StudentModule.objects.filter(course_id__exact=course_id, grade__isnull=False,
                                                  module_type__exact="problem", modified__gte=last_log_run[0].created)
        else:
            smRows = StudentModule.objects.filter(course_id__exact=course_id, grade__isnull=False,
                                                  module_type__exact="problem")

        cUpdatedRows = 0
        # For each problem, get or create the corresponding StudentModuleExpand row
        for sm in smRows:
            sme, created = StudentModuleExpand.objects.get_or_create(student=sm.student, course_id=course_id,
                                                                     module_state_key=sm.module_state_key,
                                                                     student_module=sm)

            # If the StudentModuleExpand row is new or the StudentModule row was
            # more recently updated than the StudentModuleExpand row, fill in/update
            # everything and save
            if created or (sme.modified < sm.modified):
                cUpdatedRows += 1
                sme.grade = sm.grade
                sme.max_grade = sm.max_grade
                state = json.loads(sm.state)
                sme.attempts = state["attempts"]
                sme.save()

        cAllRows = len(smRows)
        print "--------------------------------------------------------------------------------"
        print "Done! Updated/Created {0} queryable rows out of {1} from courseware_studentmodule".format(
            cUpdatedRows, cAllRows)
        print "--------------------------------------------------------------------------------"

        # Save since everything finished successfully, log latest run.
        q_log = QueryableLog(script_id=script_id, course_id=course_id, created=tstart)
        q_log.save()
