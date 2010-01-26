from zope.interface import implements, Interface, Attribute
from xtwisted.gwt.rpc import escapeString
from twisted.trial import unittest


class EscapeTest(unittest.TestCase):

    def test_standardCodes(self):
        """Verify that standard codes are escaped.
        """
        r = escapeString("\n\f\n\t\\\f\t\r")
        self.assertEquals(r, "'\\n\\f\\n\\t\\\\\\f\\t\\r'")

    def test_unicodeEscapeSmall(self):
        """Verify that unicode characters can be escaped.
        """
        r = escapeString("a\xAAa")
        self.assertEquals(r, "'a\\xaaa'")

    def test_unicodeEscapeLarge(self):
        """Verify that unicode characters can be escaped.
        """
        r = escapeString(u"\uaaa0")
        self.assertEquals(r, "'\\uaaa0'")


    def test_quoteChars(self):
        """Verify that unicode characters can be escaped.
        """
        r = escapeString(u"\"\'")
        self.assertEquals(r, "'\\\"\\\''")



