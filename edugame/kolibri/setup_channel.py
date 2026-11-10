"""
Adds a game's zip to a new channel in a throwaway Kolibri, and makes a learner.

Runs inside Kolibri (edugame kolibri-test runs it with `kolibri manage shell`), with:
EDUGAME_ZIP (the zip), EDUGAME_TITLE, EDUGAME_LEARNER and EDUGAME_PASSWORD.

This is what importing a channel from Kolibri Studio does, done by hand: the zip goes into
Kolibri's content storage under its checksum, and a channel with one HTML5 resource points at
it. Prints one line, EDUGAME_RESULT {...}, with what the browser needs to find it.
"""
import hashlib
import json
import os
import shutil
import uuid

from kolibri.core.auth.models import Facility, FacilityUser
from kolibri.core.content.models import ChannelMetadata, ContentNode, File, Language, LocalFile
from kolibri.core.content.utils.paths import get_content_storage_file_path

zip_path = os.environ["EDUGAME_ZIP"]
title = os.environ.get("EDUGAME_TITLE") or "Game"

# 1. The zip, in content storage under its checksum (as Kolibri keeps every file)
with open(zip_path, "rb") as f:
    checksum = hashlib.md5(f.read()).hexdigest()
target = get_content_storage_file_path("%s.zip" % checksum)
os.makedirs(os.path.dirname(target), exist_ok=True)
shutil.copyfile(zip_path, target)
local, _ = LocalFile.objects.get_or_create(id=checksum, defaults={
    "extension": "zip", "available": True, "file_size": os.path.getsize(target)})

# 2. A channel: a topic with one HTML5 resource in it. Channels from Studio always have a
# language, and Kolibri's HTML5 viewer needs one (without it, the resource doesn't open).
english, _ = Language.objects.get_or_create(
    id="en", defaults={"lang_code": "en", "lang_name": "English", "lang_direction": "ltr"})
channel_id = uuid.uuid4().hex
root = ContentNode.objects.create(
    id=channel_id, content_id=uuid.uuid4().hex, channel_id=channel_id,
    title="%s test channel" % title, kind="topic", available=True, lang=english)
node = ContentNode.objects.create(
    id=uuid.uuid4().hex, content_id=uuid.uuid4().hex, channel_id=channel_id, parent=root,
    title=title, kind="html5", available=True, lang=english)
File.objects.create(id=uuid.uuid4().hex, local_file=local, contentnode=node, preset="html5_zip", lang=english)
ChannelMetadata.objects.create(id=channel_id, name="%s test channel" % title, root=root, version=1)
try:  # newer Kolibris keep a few summary fields on the channel (languages, size, ...)
    from kolibri.core.content.utils.annotation import set_channel_metadata_fields
    set_channel_metadata_fields(channel_id)
except Exception as e:  # not needed to play, so carry on
    print("note: couldn't set the channel's summary fields: %r" % e)

# 3. A learner
facility = Facility.get_default_facility()
learner = FacilityUser.objects.create(username=os.environ["EDUGAME_LEARNER"], full_name="Test Learner", facility=facility)
learner.set_password(os.environ["EDUGAME_PASSWORD"])
learner.save()

print("EDUGAME_RESULT " + json.dumps({
    "channel_id": channel_id, "node_id": node.id, "content_id": node.content_id, "facility": facility.id}))
