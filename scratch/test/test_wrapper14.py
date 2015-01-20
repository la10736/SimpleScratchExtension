__author__ = 'michele'

import unittest
try:
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock
from scratch.receiver14 import tokenizer, split_message, Scratch14SensorReceiverHandler



class TestParser(unittest.TestCase):
    def test_tokenizer(self):
        """Should test the tokenizer function (generator) that
        ive the token of the body message"""
        self.assertEqual(["hello", "world"], [t for t in tokenizer("hello world")])
        self.assertEqual(["hello", "world"], [t for t in tokenizer("hello   world   ")])
        self.assertEqual(["hello world", "my", "world  "], [t for t in tokenizer('"hello world" my "world  " ')])
        self.assertEqual(['a four word string', 'embedded "quotation marks" are doubled'],
                         [t for t in tokenizer('"a four word string" "embedded ""quotation marks"" are doubled"')])
        self.assertEqual(['"'], [t for t in tokenizer('"')])
        self.assertEqual([''], [t for t in tokenizer('""')])

        self.assertEqual([12, 3, -22], [t for t in tokenizer('12 3 -22')])

        self.assertEqual([1.2, .3, -2.2, .5], [t for t in tokenizer('1.2 0.3 -2.2 .5')])

    def test_split_message(self):
        """Test the spitting message that give the (cmd, args) tuple
        - cmd is lower case insensitive without space (and character lower
        than 32)
        - args are the rest of the message
        """
        msg = "test my args test"
        self.assertEqual(("test", "my args test"), split_message(msg))
        msg = msg[:4] + chr(18) + msg[5:]
        self.assertEqual(("test", "my args test"), split_message(msg))

        msg = "TeSt my argS tESt"
        self.assertEqual(("test", "my argS tESt"), split_message(msg))

        msg = "justtest"
        self.assertEqual(("justtest", ""), split_message(msg))
        msg = "jUStteSt"
        self.assertEqual(("justtest", ""), split_message(msg))
        msg = "jUStteSt   "
        self.assertEqual(("justtest", "  "), split_message(msg))
        msg = "jUStteSt   " + chr(12) * 37
        self.assertEqual(("justtest", "  " + chr(12) * 37), split_message(msg))

    @patch("socketserver.StreamRequestHandler.__init__")
    def test_sensor_update(self,msrh):
        msrh.return_value = None
        hdl = Scratch14SensorReceiverHandler(Mock(), Mock(), Mock())
        hdl._sensor_update("a b c d")
        self.assertDictEqual(hdl.sensors, {"a": "b", "c": "d"})
        hdl._sensor_update('a "F" es')
        self.assertDictEqual(hdl.sensors, {"a": "F", "c": "d", "es": None})
        hdl._sensor_update('c "d""f" es f a')
        self.assertDictEqual(hdl.sensors, {"a": None, "c": 'd"f', "es": "f"})


if __name__ == '__main__':
    unittest.main()
