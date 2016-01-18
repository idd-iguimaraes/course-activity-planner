import os
import unittest
import tarfile
import shutil
import tempfile
import arrow

from dateutil import tz
from datetime import timedelta, time

from interpreter import Interpreter, AbsoluteTimeModifierException
from course_planner import MoodleCourse, MoodleQuiz, Seminar, Practica
from calendar_reader import CalendarReader


class InterpreterTest(unittest.TestCase):

    calendar_path = '../ActivitETS/multi-fr.ics'
    moodle_archive_path = '\
../backup-moodle2-course-1677-s20143-log792-09-20151102-1202-nu.mbz'

    def setUp(self):
        os.environ['TZ'] = 'America/Montreal'
        # Setup calendar
        calendar = CalendarReader(self.calendar_path)

        self.calendar_meetings = calendar.get_all_meetings()

        # Setup Moodle course
        self.tmp_path = tempfile.mkdtemp()
        with tarfile.open(self.moodle_archive_path) as tar_file:
            tar_file.extractall(self.tmp_path)

        self.course = MoodleCourse(self.tmp_path)
        self.interpreter = Interpreter(self.calendar_meetings, self.course)

    def tearDown(self):
        # TODO test on windows
        shutil.rmtree(self.tmp_path)

    def test_invalid_syntax(self):
        self.assertRaises(
            Exception, self.interpreter._split_line, 'Q1S1FS2S')

    def test_split_events_line(self):
        self.assertEqual(['Q1', 'S1F', 'S2S'],
                         self.interpreter._split_line('Q1 S1F S2S'))

    def test_detection_of_event(self):
        event = self.interpreter._detect_event_class_and_id('Q1')
        self.assertEqual((MoodleQuiz, 1), event)

        event = self.interpreter._detect_event_class_and_id('q13')
        self.assertEqual((MoodleQuiz, 13), event)

        event = self.interpreter._detect_event_class_and_id('p2')
        self.assertEqual((Practica, 2), event)

        event = self.interpreter._detect_event_class_and_id('P12')
        self.assertEqual((Practica, 12), event)

        event = self.interpreter._detect_event_class_and_id('s4')
        self.assertEqual((Seminar, 4), event)

        event = self.interpreter._detect_event_class_and_id('S4')
        self.assertEqual((Seminar, 4), event)

    def test_get_at_end_modifier(self):
        # Implicit start
        mods = self.interpreter._get_modifiers_as_string('S1')
        relative_modifier = mods[0]
        self.assertEqual(False, relative_modifier)

        # Explicit finish
        mods = self.interpreter._get_modifiers_as_string('S1F')
        relative_modifier = mods[0]
        self.assertEqual(True, relative_modifier)

        # Explicit finish
        mods = self.interpreter._get_modifiers_as_string('S1F@23:59')
        relative_modifier = mods[0]
        self.assertEqual(True, relative_modifier)

        # Implicit start
        mods = self.interpreter._get_modifiers_as_string('S1-1d')
        relative_modifier = mods[0]
        self.assertEqual(False, relative_modifier)

        # Explicit finish
        mods = self.interpreter._get_modifiers_as_string('S1F+1D@23:59')
        at_end = mods[0]
        self.assertEqual(True, at_end)

        # Explicit start
        mods = self.interpreter._get_modifiers_as_string('S1S+1D@23:59')
        at_end = mods[0]
        self.assertEqual(False, at_end)

        # Implicit start
        mods = self.interpreter._get_modifiers_as_string('S1+1D@23:59')
        at_end = mods[0]
        self.assertEqual(False, at_end)

    def test_get_relative_modifier_as_string(self):
        mods = self.interpreter._get_modifiers_as_string('S1')
        relative_modifier = mods[1]
        self.assertEqual(None, relative_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F')
        relative_modifier = mods[1]
        self.assertEqual(None, relative_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F@23:59')
        relative_modifier = mods[1]
        self.assertEqual(None, relative_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F-1d')
        relative_modifier = mods[1]
        self.assertEqual('-1d', relative_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F+1D@23:59')
        relative_modifier = mods[1]
        self.assertEqual('+1D', relative_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1S+1h@23:59')
        relative_modifier = mods[1]
        self.assertEqual('+1h', relative_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1-13243m@23:59')
        relative_modifier = mods[1]
        self.assertEqual('-13243m', relative_modifier)

    def test_get_time_modifier_as_string(self):
        mods = self.interpreter._get_modifiers_as_string('S1')
        time_modifier = mods[2]
        self.assertEqual(None, time_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F')
        time_modifier = mods[2]
        self.assertEqual(None, time_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F-1d')
        time_modifier = mods[2]
        self.assertEqual(None, time_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F@10:59')
        time_modifier = mods[2]
        self.assertEqual('10:59', time_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1F+1D@23:59')
        time_modifier = mods[2]
        self.assertEqual('23:59', time_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1S+1h@22:11')
        time_modifier = mods[2]
        self.assertEqual('22:11', time_modifier)

        mods = self.interpreter._get_modifiers_as_string('S1-13243m@3:01')
        time_modifier = mods[2]
        self.assertEqual('3:01', time_modifier)

    def test_interpret_time_modifier(self):
        self.assertEqual(
            time(hour=3, minute=1),
            self.interpreter._interpret_time_modifier('3:01'))

        self.assertEqual(
            time(hour=15, minute=59),
            self.interpreter._interpret_time_modifier('15:59'))

        self.assertEqual(
            time(hour=23, minute=59),
            self.interpreter._interpret_time_modifier('23:59'))

        self.assertEqual(
            time(hour=1, minute=1),
            self.interpreter._interpret_time_modifier('01:1'))

    def test_interpret_invalid_time_modifier(self):
        self.assertRaises(
            AbsoluteTimeModifierException,
            self.interpreter._interpret_time_modifier, '24:00')

        self.assertRaises(
            AbsoluteTimeModifierException,
            self.interpreter._interpret_time_modifier, '23:60')

        self.assertRaises(
            AbsoluteTimeModifierException,
            self.interpreter._interpret_time_modifier, '12:63')

    def test_interpret_relative_modifier(self):
        self.assertEqual(
            timedelta(days=1),
            self.interpreter._interpret_relative_modifier('1d'))

        self.assertEqual(
            timedelta(days=-2),
            self.interpreter._interpret_relative_modifier('-2d'))

        self.assertEqual(
            timedelta(hours=123),
            self.interpreter._interpret_relative_modifier('0123h'))

        self.assertEqual(
            timedelta(hours=-23),
            self.interpreter._interpret_relative_modifier('-23h'))

        self.assertEqual(
            timedelta(minutes=-50),
            self.interpreter._interpret_relative_modifier('-050m'))

        self.assertEqual(
            timedelta(minutes=106),
            self.interpreter._interpret_relative_modifier('106m'))

    def test_build_new_date_from_event(self):
        expected = arrow.get(2000, 1, 1, 0, 1).datetime
        actual = self.interpreter._get_new_datetime(
            arrow.get(2000, 1, 1).datetime, timedelta(minutes=1), None)
        self.assertEqual(expected, actual)

        expected = arrow.get(2000, 1, 1).datetime
        actual = self.interpreter._get_new_datetime(
            arrow.get(2000, 1, 1, 0, 2).datetime, timedelta(minutes=-2), None)
        self.assertEqual(expected, actual)

        expected = arrow.get(2000, 1, 1, 3).datetime
        actual = self.interpreter._get_new_datetime(
            arrow.get(2000, 1, 1).datetime, timedelta(hours=3), None)
        self.assertEqual(expected, actual)

        expected = arrow.get(1999, 12, 31).datetime
        actual = self.interpreter._get_new_datetime(
            arrow.get(2000, 1, 1).datetime, timedelta(days=-1), None)
        self.assertEqual(expected, actual)

        expected = arrow.get(2000, 1, 1, 2, 5).datetime
        actual = self.interpreter._get_new_datetime(
            arrow.get(2000, 1, 1).datetime, None, time(hour=2, minute=5))
        self.assertEqual(expected, actual)

        expected = arrow.get(2000, 1, 2, 2, 5).datetime
        actual = self.interpreter._get_new_datetime(
            arrow.get(2000, 1, 1, 0, 0, 0).datetime, timedelta(days=1),
            time(hour=2, minute=5))
        self.assertEqual(expected, actual)

        expected = arrow.get(1999, 12, 31, 23, 55).datetime
        actual = self.interpreter._get_new_datetime(
            arrow.get(2000, 1, 1).datetime, timedelta(days=-1),
            time(hour=23, minute=55))
        self.assertEqual(expected, actual)

    def test_get_subject(self):
        tokens = self.interpreter._split_line('Q1 S1 S1F')
        actual = self.interpreter._parse_subject(tokens)['id']
        self.assertEqual('4271', actual)

        tokens = self.interpreter._split_line('Q2 S1 S1F')
        actual = self.interpreter._parse_subject(tokens)['id']
        self.assertEqual('4272', actual)

        tokens = self.interpreter._split_line('Q3 S1 S1F')
        actual = self.interpreter._parse_subject(tokens)['id']
        self.assertEqual('4273', actual)

    def test_get_subject_with_applied_modifiers(self):
        # TODO modify end dates
        expected = arrow.get(
            2014, 1, 6, 7, tzinfo=tz.gettz('America/Montreal')).datetime

        actual = self.interpreter.apply('Q1 S1 S1F').get_start_datetime()
        self.assertEqual(expected, actual)

        expected = arrow.get(
            2014, 1, 13, 7, tzinfo=tz.gettz('America/Montreal')).datetime
        actual = self.interpreter.apply('Q1 S2 S3F').get_start_datetime()
        self.assertEqual(expected, actual)

        expected = arrow.get(
            2014, 1, 20, 8, tzinfo=tz.gettz('America/Montreal')).datetime
        actual = self.interpreter.apply('Q1 S3F S4F').get_start_datetime()
        self.assertEqual(expected, actual)
