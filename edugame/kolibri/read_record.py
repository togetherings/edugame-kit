"""
Prints what Kolibri recorded about a learner and a resource, as EDUGAME_RESULT {...}.

Runs inside Kolibri (edugame kolibri-test runs it with `kolibri manage shell`), with
EDUGAME_CONTENT_ID and EDUGAME_LEARNER. Kolibri's HTML5 viewer keeps what a game sends
through SCORM in the learner's ContentSummaryLog (extra_fields.contentState.SCORM.cmi).
"""
import json
import os

from kolibri.core.auth.models import FacilityUser
from kolibri.core.logger.models import ContentSummaryLog

user = FacilityUser.objects.get(username=os.environ["EDUGAME_LEARNER"])
log = ContentSummaryLog.objects.filter(user=user, content_id=os.environ["EDUGAME_CONTENT_ID"]).first()
out = {"found": log is not None}
if log is not None:
    cmi = (((log.extra_fields or {}).get("contentState") or {}).get("SCORM") or {}).get("cmi") or {}
    core = cmi.get("core") or {}
    out.update({
        "progress": log.progress,
        "time_spent": log.time_spent,
        "status": core.get("lesson_status"),
        "exit": core.get("exit"),
        "score_raw": (core.get("score") or {}).get("raw"),
        "suspend_data": cmi.get("suspend_data") or "",
    })
print("EDUGAME_RESULT " + json.dumps(out))
