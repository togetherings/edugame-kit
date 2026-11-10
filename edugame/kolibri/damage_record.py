"""
Damages a learner's save in a throwaway Kolibri, as a save cut off on its way would be.

Runs inside Kolibri (edugame kolibri-test runs it with `kolibri manage shell`), with
EDUGAME_CONTENT_ID and EDUGAME_LEARNER. Cuts SCORM suspend_data in half in the learner's
ContentSummaryLog, and prints EDUGAME_RESULT {"damaged": "<what it is now>"}.
"""
import json
import os

from kolibri.core.auth.models import FacilityUser
from kolibri.core.logger.models import ContentSummaryLog

user = FacilityUser.objects.get(username=os.environ["EDUGAME_LEARNER"])
log = ContentSummaryLog.objects.get(user=user, content_id=os.environ["EDUGAME_CONTENT_ID"])
extra = log.extra_fields or {}
cmi = extra.setdefault("contentState", {}).setdefault("SCORM", {}).setdefault("cmi", {})
text = cmi.get("suspend_data") or ""
cmi["suspend_data"] = text[: max(1, len(text) // 2)]
log.extra_fields = extra
log.save()
print("EDUGAME_RESULT " + json.dumps({"damaged": cmi["suspend_data"]}))
