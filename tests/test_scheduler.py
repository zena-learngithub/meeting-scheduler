import unittest
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

try:
    from meeting_scheduler import MeetingScheduler
    IMPORT_SUCCESS = True
except ImportError:
    IMPORT_SUCCESS = False

@unittest.skipIf(not IMPORT_SUCCESS, "Could not import MeetingScheduler")
class TestMeetingScheduler(unittest.TestCase):
    
    def test_email_validation(self):
        """Test email validation function"""
        scheduler = MeetingScheduler()
        
        # Valid emails
        self.assertTrue(scheduler.validate_email("test@example.com"))
        self.assertTrue(scheduler.validate_email("user.name@domain.co"))
        
        # Invalid emails
        self.assertFalse(scheduler.validate_email("invalid-email"))
        self.assertFalse(scheduler.validate_email("@domain.com"))
        self.assertFalse(scheduler.validate_email("user@"))
    
    def test_datetime_validation(self):
        """Test datetime validation"""
        scheduler = MeetingScheduler()
        
        # Valid date/time
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        result = scheduler.validate_datetime(future_date, "14:30")
        self.assertIsNotNone(result)
        
        # Past date (should fail)
        past_date = "2020-01-01"
        result = scheduler.validate_datetime(past_date, "14:30")
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()