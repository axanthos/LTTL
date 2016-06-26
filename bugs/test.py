import sys
import unittest

class TestAssertCountEqual(unittest.TestCase):
    def test(self):
        self.assertCountEqual((1, 2), [2, 1])
        
    def assertCountEqual(self, iterable1, iterable2):
        if (sys.version_info > (3, 0)):
            return super(TestAssertCountEqual, self).assertCountEqual(
                iterable1,
                iterable2,
            )
        else:
            return super(TestAssertCountEqual, self).assertItemsEqual(
                iterable1,
                iterable2,
            )

        
if __name__ == '__main__':
    unittest.main(verbosity=42)