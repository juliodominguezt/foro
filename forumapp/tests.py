import datetime, json
from contextlib import contextmanager
from django.test import TestCase, Client
from django.core.exceptions import ValidationError

from django.utils import timezone
from django.urls import reverse

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import Channel, Thread, Comment, UserSettings

#Allow easy testing for validation errors
class ValidationErrorTestMixin(object):
    @contextmanager
    def assertValidationErrors(self, fields):
        try:
            yield
            raise AssertionError("ValidationError not raised")

        except ValidationError as e:
            self.assertEqual(set(fields), set(e.message_dict.keys()))

## Helper functions
def create_channel(name, owner, desc="testdesc", days=0):
    time = timezone.now() + datetime.timedelta(days=days)
    return Channel.objects.create(channel_name=name, owner=owner, description=desc, pub_date=time)

def create_thread(channel, owner, name="thread123", desc="testdesc", days=0):
    time = timezone.now() + datetime.timedelta(days=days)
    return Thread.objects.create(channel=channel, owner=owner, thread_name=name, description=desc, pub_date=time)

def create_comment(thread, owner, text="text", days=0):
    time = timezone.now() + datetime.timedelta(days=days)
    return Comment.objects.create(thread=thread, text=text, owner=owner, pub_date=time)

##TODO: create_reply

## Channel tests
class ChannelTests(ValidationErrorTestMixin, TestCase):
    channel_name = "Test-channel-123456789"
    channel_name2 = channel_name[:8]
    channel_desc = "description"
    username = 'owner'
    username2 = 'other'

    def testNoChannel(self):
        response = self.client.get(reverse('forumapp:channel'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No channels are available.")
        self.assertQuerysetEqual(response.context['channel_list'], [])

    def testChannelCreateDelete(self):
        owner = User.objects.create(username=self.username)

        c = create_channel(self.channel_name, owner)

        self.assertIn(c.channel_name, self.channel_name)
        self.assertEqual(len(c.channel_name), len(self.channel_name))

        response = self.client.get(reverse('forumapp:channel'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.channel_name)

        c.delete()

        self.testNoChannel()

    def testChannelIsRecent(self):
        owner = User.objects.create(username=self.username)

        c = create_channel(self.channel_name, owner)

        self.assertTrue(c.is_recent())

        c.pub_date = timezone.now() - datetime.timedelta(days=2)
        c.save()

        self.assertFalse(c.is_recent())

        c.pub_date = timezone.now() + datetime.timedelta(days=2)
        c.save()

        self.assertFalse(c.is_recent())

    def testChannelsAreDisplayed(self):
        owner = User.objects.create(username=self.username)

        c = create_channel(self.channel_name, owner)
        c = create_channel(self.channel_name2, owner)

        response = self.client.get(reverse('forumapp:channel'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.channel_name)
        self.assertContains(response, self.channel_name2)

    ## Tests whether a channel is correctly passed off to one of the channel moderators
    ## if a channel moderator is specified when the owner is deleted
    def testChannelOwnerPassOff(self):
        owner = User.objects.create(username=self.username)
        otheruser = User.objects.create(username=self.username[::-1])

        channel = create_channel(self.channel_name, owner)
        subthread = create_thread(channel, owner)

        # set moderator
        channel.moderators = json.dumps([otheruser.username])
        channel.save()

        #delete channel and see if the owner was changed to to the otheruser
        owner.delete()

        self.assertTrue(Channel.objects.filter(channel_name=self.channel_name).exists())
        self.assertEqual(self.username[::-1], Channel.objects.get(channel_name=self.channel_name).owner.username)

    def testUniqueChannel(self):
        user1 = User.objects.create(username=self.username)
        user2 = User.objects.create(username=self.username2)
        c1 = create_channel(self.channel_name, user1)
        c2 = create_channel(self.channel_name2, user2)
        c3 = Channel(channel_name=self.channel_name, owner=user1, pub_date=timezone.now())
        c4 = Channel(channel_name=self.channel_name2, owner=user1, pub_date=timezone.now())

        with self.assertValidationErrors(['channel_name']):
            c3.validate_unique()

        with self.assertValidationErrors(['channel_name']):
            c4.validate_unique()

    def testAdminRemoveChannel(self):
        pass

    # users SHOULD be able to remove their own channels
    def testOwnerRemoveChannel(self):
        pass
'''
    def testCreateChannelUsingForm(self):
        password = "P@ssw0rd1"
        response = self.client.post(reverse('forumapp:channel'), {'channel_name': self.channel_name, 'description': self.channel_desc}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['user'].is_authenticated)
        self.assertContains(response, 'Please log in to create channels')

        User.objects.create_user(username=self.username, password=password)
        self.client.login(username=self.username, password=password)

        response = self.client.post(reverse('forumapp:channel'), {'channel_name': self.channel_name2, 'description': self.channel_desc}, follow=True)
        #print(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertContains(response, self.channel_name2)
        self.assertContains(response, self.channel_desc)
'''

## Thread tests
class ThreadTests(ValidationErrorTestMixin, TestCase):
    channel_name = "channelfortestthread"
    channel_name2 = channel_name[:8]
    username = 'owner'
    username2 = 'other'
    thread_name = "threadtest"
    thread_desc = "descriptionforthreadtest"

    def testNoThread(self):
        owner = User.objects.create(username=self.username)
        c = create_channel(self.channel_name, owner)

        response = self.client.get(reverse('forumapp:thread', kwargs={'channel': self.channel_name}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No threads are available.")
        self.assertQuerysetEqual(response.context['thread_list'], [])

    def testThreadCreateDelete(self):
        owner = User.objects.create(username=self.username)
        c = create_channel(self.channel_name, owner)
        t = create_thread(c, owner, self.thread_name, self.thread_desc)

        self.assertIn(t.thread_name, self.thread_name)
        self.assertEqual(len(t.thread_name), len(self.thread_name))
        self.assertEqual(t.__str__(), self.thread_name)

        response = self.client.get(reverse('forumapp:thread', kwargs={'channel': self.channel_name}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.thread_name)

        c.delete()

        response = self.client.get(reverse('forumapp:thread', kwargs={'channel': self.channel_name}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No threads are available.")
        self.assertQuerysetEqual(response.context['thread_list'], [])

    def testThreadIsRecent(self):
        owner = User.objects.create(username=self.username)
        c = create_channel(self.channel_name, owner)
        t = create_thread(c, owner, self.thread_name, self.thread_desc)

        self.assertTrue(t.is_recent())

        t.pub_date = timezone.now() - datetime.timedelta(days=2)
        t.save()

        self.assertFalse(t.is_recent())

        t.pub_date = timezone.now() + datetime.timedelta(days=2)
        t.save()

        self.assertFalse(t.is_recent())

    def testThreadsAreDisplayed(self):
        owner = User.objects.create(username=self.username+'2')
        c = create_channel(self.channel_name, owner, -1)
        t1 = create_thread(c, owner, self.thread_name, self.thread_desc)
        t2 = create_thread(c, owner, self.thread_name[::-1], self.thread_desc)

        self.assertEqual(0, t1.thread_id)
        self.assertEqual(1, t2.thread_id)

        response = self.client.get(reverse('forumapp:thread', kwargs={'channel': self.channel_name}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.thread_name)
        self.assertContains(response, self.thread_name[::-1])

    ## Test whether deleting a thread preserves its channel and deletes its comments
    def testThreadDelete(self):
        owner = User.objects.create(username=self.username)

        # Create a channel
        channel = create_channel(self.channel_name, owner)
        thread = create_thread(channel, owner, self.thread_name)
        thread_id = thread.thread_id

        comment = create_comment(thread, owner)
        comment_id = comment.comment_id

        thread.delete()

        self.assertTrue(User.objects.filter(username=self.username).exists())
        self.assertTrue(Channel.objects.filter(channel_name=self.channel_name).exists())
        self.assertFalse(Thread.objects.filter(channel__channel_name=self.channel_name, thread_id=thread_id).exists())
        self.assertFalse(Thread.objects.filter(channel=None).exists())
        self.assertFalse(Comment.objects.filter(thread__thread_id=thread_id, comment_id=comment_id).exists())
        self.assertFalse(Comment.objects.filter(thread=None).exists())

    # Confirm that threadss are unique on (channel, thread_id)
    def testUniqueThread(self):
        user1 = User.objects.create(username=self.username)
        user2 = User.objects.create(username=self.username2)
        c1 = create_channel(self.channel_name, user1)
        c2 = create_channel(self.channel_name2, user2)
        t1 = create_thread(c1, user1)
        t2 = create_thread(c1, user1)
        t3 = create_thread(c2, user2)
        t4 = create_thread(c2, user1)

        self.assertEqual(t1.thread_id, t3.thread_id)
        self.assertEqual(t2.thread_id, t4.thread_id)

        t5 = Thread(thread_id=0, channel=c1, owner=user2, thread_name="aa", description="bb", pub_date=timezone.now())

        with self.assertValidationErrors(['channel', 'thread_id']):
            t5.validate_unique()

    def testAdminRemoveThread(self):
        pass

    # users SHOULD be able to remove their own threads
    def testOwnerRemoveThread(self):
        pass
'''
    def testCreateThreadUsingForm(self):
        password = "P@ssw0rd1"
        user = User.objects.create_user(username=self.username, password=password)

        self.client.login(username=self.username, password=password)
        ch = create_channel(self.channel_name, user)

        response = self.client.post(reverse('forumapp:thread', kwargs={'channel': ch.channel_name}), {'thread_name': self.thread_name, 'description': self.thread_desc}, follow=True)

        #print(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertContains(response, self.thread_name)
        self.assertContains(response, self.thread_desc)
'''

## Comment tests
class CommentTests(ValidationErrorTestMixin, TestCase):
    username = "testuser3"
    username2 = "testuser4"
    username3 = "testuser5"
    channel_name = "aaatestchannel"
    channel_name2 = channel_name[:8]
    text = "test text :)"

    def testNoComment(self):
        owner = User.objects.create(username=self.username)

        channel = create_channel(self.channel_name, owner)
        owner2 = User.objects.create(username=self.username2)
        thread = create_thread(channel, owner2)

        response = self.client.get(reverse('forumapp:comment', kwargs={'channel': channel.channel_name, 'thread': thread.thread_id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No comments are available.")
        self.assertQuerysetEqual(response.context['comment_list'], [])

    def testCommentCreateDelete(self):
        owner = User.objects.create(username=self.username)

        channel = create_channel(self.channel_name, owner)
        owner2 = User.objects.create(username=self.username2)
        thread = create_thread(channel, owner2)
        owner3 = User.objects.create(username=self.username3)

        c = create_comment(thread, owner3, self.text)

        self.assertEqual(c.__str__(), self.text)

        response = self.client.get(reverse('forumapp:comment', kwargs={'channel': self.channel_name, 'thread': thread.thread_id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.text)
        self.assertContains(response, self.username3)

        c.delete()

        response = self.client.get(reverse('forumapp:comment', kwargs={'channel': self.channel_name, 'thread': thread.thread_id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No comments are available.")
        self.assertQuerysetEqual(response.context['comment_list'], [])

    def testCommentsAreDisplayed(self):
        owner = User.objects.create(username=self.username)
        channel = create_channel(self.channel_name, owner)
        owner2 = User.objects.create(username=self.username2)
        thread = create_thread(channel, owner2)
        owner3 = User.objects.create(username=self.username3)


        c1 = create_comment(thread, owner3, self.text)
        c2 = create_comment(thread, owner2, self.text[::-1])

        self.assertEqual(0, c1.comment_id)
        self.assertEqual(1, c2.comment_id)

        response = self.client.get(reverse('forumapp:comment', kwargs={'channel': self.channel_name, 'thread': thread.thread_id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.text)
        self.assertContains(response, self.text[::-1])

    ## Test whether deleting a comment preserves its thread
    def testCommentDelete(self):
        owner = User.objects.create(username=self.username)

        # Create a channel
        channel = create_channel(self.channel_name, owner)
        thread = create_thread(channel, owner)
        thread_id = thread.thread_id

        comment = create_comment(thread, owner)
        comment_id = comment.comment_id

        comment.delete()

        self.assertTrue(User.objects.filter(username=self.username).exists())
        self.assertTrue(Channel.objects.filter(channel_name=self.channel_name).exists())
        self.assertTrue(Thread.objects.filter(channel__channel_name=self.channel_name, thread_id=thread_id).exists())
        self.assertFalse(Comment.objects.filter(thread__thread_id=thread_id, comment_id=comment_id).exists())
        self.assertFalse(Comment.objects.filter(thread=None).exists())

    def testCommentIsRecent(self):
        owner = User.objects.create(username=self.username)
        channel = create_channel(self.channel_name, owner)
        owner2 = User.objects.create(username=self.username2)
        thread = create_thread(channel, owner2)
        owner3 = User.objects.create(username=self.username3)

        c1 = create_comment(thread, owner3, days=-2)
        c2 = create_comment(thread, owner3, days=-0.5)
        c3 = create_comment(thread, owner2, days=0)
        c4 = create_comment(thread, owner, days=1)

        response = self.client.get(reverse('forumapp:comment', kwargs={'channel': self.channel_name, 'thread': thread.thread_id}))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(c1.is_recent())
        self.assertTrue(c2.is_recent())
        self.assertTrue(c3.is_recent())
        self.assertFalse(c4.is_recent())

    # Confirm that comments are unique on (thread, comment_id)
    def testUniqueComment(self):
        user1 = User.objects.create(username=self.username)
        user2 = User.objects.create(username=self.username2)
        c1 = create_channel(self.channel_name, user1)
        c2 = create_channel(self.channel_name2, user2)
        t1 = create_thread(c1, user1)
        t2 = create_thread(c2, user2)
        co1 = create_comment(t1, user1)
        co2 = create_comment(t1, user2)
        co3 = create_comment(t2, user2)
        co4 = create_comment(t2, user2)

        self.assertEqual(co1.comment_id, co3.comment_id)
        self.assertEqual(co2.comment_id, co4.comment_id)

        co5 = Comment(comment_id=0, thread=t1, owner=user2, text="", pub_date=timezone.now())
        co6 = Comment(comment_id=1, thread=t1, owner=user2, text="", pub_date=timezone.now())
        co7 = Comment(comment_id=1, thread=t2, owner=user1, text="", pub_date=timezone.now())

        with self.assertValidationErrors(['thread', 'comment_id']):
            co5.validate_unique()

        with self.assertValidationErrors(['thread', 'comment_id']):
            co6.validate_unique()

        with self.assertValidationErrors(['thread', 'comment_id']):
            co7.validate_unique()

    def testAdminRemoveComment(self):
        pass

    # users SHOULD NOT be able to remove their own comments
    def testOwnerRemoveComment(self):
        pass

'''
    def testCreateCommentUsingForm(self):
        password = "P@ssw0rd1"
        user = User.objects.create_user(username=self.username, password=password)

        self.client.login(username=self.username, password=password)
        ch = create_channel(self.channel_name, user)
        th = create_thread(ch, user)

        response = self.client.post(reverse('forumapp:comment', kwargs={'channel': ch.channel_name, 'thread': th.thread_id}), {'text': self.text}, follow=True)

        #print(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertContains(response, self.text)
'''

class UserTests(ValidationErrorTestMixin, TestCase):
    username = "randomuser91387245"
    username2 = "asfghjguser"
    channel_name = "channel1981719"
    channel_name2 = "asfsga"

    ## Preserve data when a User is deleted
    ## Cascade-delete when channels/threads are removed (preserving users)
    def testUserDelete(self):
        owner = User.objects.create(username=self.username)
        otheruser = User.objects.create(username=self.username[::-1])

        # Create a channel
        channel = create_channel(self.channel_name, owner)
        subthread = create_thread(channel, owner)
        thread_id1 = subthread.thread_id

        subcomment = create_comment(subthread, owner)
        comment_id1 = subcomment.comment_id

        # Create a thread under another users channel
        otherchannel = create_channel(self.channel_name2, otheruser)
        thread = create_thread(otherchannel, owner)


        # Create a comment under another users channel and thread
        otherthread = create_thread(otherchannel, otheruser)
        thread_id2 = otherthread.thread_id

        otherthread_id = otherthread.thread_id
        comment = create_comment(otherthread, owner)
        comment_id2 = comment.comment_id

        owner.delete()

        # Channel and its children should be gone (this tests cascade deletion
        #   for channels->threads->comments)
        self.assertFalse(Channel.objects.filter(owner=None).exists())
        self.assertFalse(Thread.objects.filter(channel=None).exists())
        self.assertFalse(Comment.objects.filter(thread=None).exists())

        # Verify that the thread and comment under the other user's channel should still exist
        self.assertTrue(Channel.objects.filter(channel_name=self.channel_name2).exists())
        self.assertTrue(Thread.objects.filter(channel__channel_name=self.channel_name2, thread_id=thread_id2).exists())
        self.assertTrue(Comment.objects.filter(thread__channel__channel_name=self.channel_name2, thread__thread_id=otherthread_id, comment_id=comment_id2).exists())

    def testUniqueUser(self):
        user1 = User.objects.create(username=self.username)
        user2 = User.objects.create(username=self.username2)

        with self.assertValidationErrors(['username']):
            User(username=self.username).validate_unique()

    def testUserSettings(self):
        user = User.objects.create(username=self.username)
        usersettings = UserSettings.objects.create(user=user)
        self.assertEqual(usersettings.__str__(), self.username)

    def testAdminBanUser(self):
        pass

    def testChannelBanUser(self):
        pass
