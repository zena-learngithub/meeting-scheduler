"""
Meeting Scheduler - Command Line Application
Author: Zenawi Zemene
Version: 2.0.0 (Secure)
Date: 2023

A secure meeting scheduler application with no hardcoded credentials.
Uses environment variables and local config files for sensitive data.
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# Configuration
USER_DATA_DIR = Path("user_data")
MEETINGS_FILE = USER_DATA_DIR / "meetings.json"
CONFIG_FILE = USER_DATA_DIR / "email_config.json"

class MeetingScheduler:
    def __init__(self):
        """Initialize the Meeting Scheduler application."""
        # Create user data directory if it doesn't exist
        USER_DATA_DIR.mkdir(exist_ok=True)
        
        # Load configuration (environment variables + local config)
        self.email_config = self.load_configuration()
        self.meetings = self.load_meetings()
        self.running = True
        
    def load_configuration(self) -> Dict:
        """
        Load email configuration from multiple sources in order of priority:
        1. Environment variables (highest priority)
        2. Local config file (medium priority)
        3. Default values (lowest priority)
        """
        # Default configuration (NO PASSWORDS HERE)
        config = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "sender_email": "",
            "sender_password": ""
        }
        
        # Override with environment variables if they exist
        env_config = {
            "smtp_server": os.getenv("SMTP_SERVER"),
            "smtp_port": os.getenv("SMTP_PORT"),
            "use_tls": os.getenv("USE_TLS"),
            "sender_email": os.getenv("EMAIL_USER"),
            "sender_password": os.getenv("EMAIL_PASS")
        }
        
        for key, value in env_config.items():
            if value is not None:
                if key == "smtp_port":
                    try:
                        config[key] = int(value)
                    except ValueError:
                        print(f"Warning: Invalid port '{value}', using default")
                elif key == "use_tls":
                    config[key] = value.lower() in ["true", "yes", "1", "t"]
                else:
                    config[key] = value
        
        # Override with local config file if it exists
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load config file: {e}")
        
        return config
    
    def load_meetings(self) -> Dict:
        """Load meetings from JSON file."""
        if MEETINGS_FILE.exists():
            try:
                with open(MEETINGS_FILE, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                print("Warning: Could not load meetings data. Starting fresh.")
                return {}
        return {}
    
    def save_meetings(self):
        """Save meetings to JSON file."""
        try:
            with open(MEETINGS_FILE, 'w') as f:
                json.dump(self.meetings, f, indent=2, default=str)
        except IOError as e:
            print(f"Error saving meetings: {e}")
    
    def save_configuration(self):
        """Save current configuration to local config file."""
        try:
            # Don't save empty credentials
            config_to_save = {
                k: v for k, v in self.email_config.items()
                if not (k.endswith("_password") and not v)  # Skip empty passwords
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_to_save, f, indent=2)
        except IOError as e:
            print(f"Error saving configuration: {e}")
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Validate and parse date and time strings."""
        try:
            # Try multiple date formats
            for date_format in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:
                try:
                    date_obj = datetime.strptime(date_str, date_format)
                    break
                except ValueError:
                    continue
            else:
                print("Error: Invalid date format. Use YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY")
                return None
            
            # Parse time
            for time_format in ["%H:%M", "%I:%M%p", "%I:%M %p"]:
                try:
                    time_obj = datetime.strptime(time_str, time_format)
                    break
                except ValueError:
                    continue
            else:
                print("Error: Invalid time format. Use HH:MM or HH:MM AM/PM")
                return None
            
            # Combine date and time
            combined = datetime.combine(date_obj.date(), time_obj.time())
            
            # Check if time is in the future
            if combined < datetime.now():
                print("Error: Meeting time must be in the future.")
                return None
            
            return combined
        except Exception as e:
            print(f"Error parsing datetime: {e}")
            return None
    
    def check_time_conflict(self, meeting_datetime: datetime, duration_minutes: int, exclude_id: str = None) -> bool:
        """Check if there's a time conflict with existing meetings."""
        end_time = meeting_datetime + timedelta(minutes=duration_minutes)
        
        for meeting_id, meeting in self.meetings.items():
            if meeting_id == exclude_id:
                continue
            
            if meeting["status"] not in ["scheduled", "rescheduled"]:
                continue
            
            existing_start = datetime.fromisoformat(meeting["datetime"])
            existing_duration = meeting["duration_minutes"]
            existing_end = existing_start + timedelta(minutes=existing_duration)
            
            # Check for overlap
            if (meeting_datetime < existing_end and end_time > existing_start):
                return True
        
        return False
    
    def send_email_notification(self, recipient: str, subject: str, body: str) -> bool:
        """Send email notification about meeting."""
        if not self.email_config.get("sender_email") or not self.email_config.get("sender_password"):
            print("\nEmail not configured. Please configure email settings first.")
            print("You can still schedule meetings, but email notifications won't be sent.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.email_config["sender_email"]
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to server and send
            server = smtplib.SMTP(self.email_config["smtp_server"], self.email_config["smtp_port"])
            
            if self.email_config.get("use_tls", True):
                server.starttls()
            
            server.login(self.email_config["sender_email"], self.email_config["sender_password"])
            server.send_message(msg)
            server.quit()
            
            print(f"✓ Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("✗ Email authentication failed. Please check your email and password.")
            return False
        except Exception as e:
            print(f"✗ Failed to send email: {e}")
            return False
    
    def schedule_meeting(self):
        """Schedule a new meeting."""
        print("\n" + "="*50)
        print("SCHEDULE A NEW MEETING")
        print("="*50)
        
        # Get meeting title
        while True:
            title = input("Meeting title: ").strip()
            if title:
                break
            print("Error: Title cannot be empty.")
        
        # Get meeting description
        description = input("Meeting description (optional): ").strip()
        
        # Get participant emails
        participants = []
        print("\nEnter participant emails (enter 'done' when finished):")
        while True:
            email = input("Email: ").strip()
            if email.lower() == 'done':
                if not participants:
                    print("At least one participant is required.")
                    continue
                break
            
            if self.validate_email(email):
                participants.append(email)
                print(f"✓ Added: {email}")
            else:
                print("Invalid email format. Please try again.")
        
        # Get date and time
        while True:
            print("\nEnter meeting date and time:")
            date_str = input("Date (YYYY-MM-DD): ").strip()
            time_str = input("Time (HH:MM or HH:MM AM/PM): ").strip()
            
            meeting_datetime = self.validate_datetime(date_str, time_str)
            if meeting_datetime:
                break
        
        # Get duration
        while True:
            try:
                duration = int(input("Duration (minutes): ").strip())
                if duration > 0:
                    break
                print("Duration must be positive.")
            except ValueError:
                print("Please enter a valid number.")
        
        # Check for time conflicts
        if self.check_time_conflict(meeting_datetime, duration):
            print("\nWarning: There's a time conflict with an existing meeting!")
            proceed = input("Do you want to schedule anyway? (yes/no): ").strip().lower()
            if proceed != 'yes':
                print("Meeting scheduling cancelled.")
                return
        
        # Generate unique ID
        meeting_id = str(uuid.uuid4())[:8]
        
        # Create meeting object
        meeting = {
            "id": meeting_id,
            "title": title,
            "description": description,
            "participants": participants,
            "datetime": meeting_datetime.isoformat(),
            "duration_minutes": duration,
            "status": "scheduled",
            "created_at": datetime.now().isoformat()
        }
        
        # Save meeting
        self.meetings[meeting_id] = meeting
        self.save_meetings()
        
        print(f"\n✓ Meeting scheduled successfully! Meeting ID: {meeting_id}")
        
        # Check if email is configured
        can_send_email = bool(self.email_config.get("sender_email") and self.email_config.get("sender_password"))
        
        if can_send_email:
            send_emails = input("\nSend email notifications to participants? (yes/no): ").strip().lower()
            if send_emails == 'yes':
                email_count = 0
                for participant in participants:
                    subject = f"Meeting Scheduled: {title}"
                    body = f"""Hello,

A new meeting has been scheduled:

Title: {title}
Description: {description}
Date: {meeting_datetime.strftime('%B %d, %Y')}
Time: {meeting_datetime.strftime('%I:%M %p')}
Duration: {duration} minutes
Meeting ID: {meeting_id}

Please mark your calendar.

Best regards,
Meeting Scheduler
"""
                    if self.send_email_notification(participant, subject, body):
                        email_count += 1
                
                print(f"\n✓ Sent {email_count} email notification(s)")
        else:
            print("\nEmail not configured. No notifications sent.")
            print("Use option 8 to configure email for future meetings.")
    
    def list_meetings(self, filter_status: str = None):
        """List all meetings, optionally filtered by status."""
        print("\n" + "="*50)
        print("MEETINGS")
        print("="*50)
        
        if not self.meetings:
            print("No meetings found.")
            return
        
        # Filter meetings if needed
        meetings_to_show = self.meetings
        if filter_status:
            meetings_to_show = {k: v for k, v in self.meetings.items() if v["status"] == filter_status}
        
        if not meetings_to_show:
            print(f"No {filter_status} meetings found.")
            return
        
        # Sort by date
        sorted_meetings = sorted(
            meetings_to_show.items(),
            key=lambda x: datetime.fromisoformat(x[1]["datetime"])
        )
        
        for meeting_id, meeting in sorted_meetings:
            meeting_datetime = datetime.fromisoformat(meeting["datetime"])
            
            # Status emoji
            status_emoji = {
                "scheduled": "Y",
                "rescheduled": "R",
                "cancelled": "X"
            }.get(meeting['status'], '❓')
            
            print(f"\n{status_emoji} [{meeting['status'].upper()}] ID: {meeting_id}")
            print(f"   Title: {meeting['title']}")
            print(f"   Date: {meeting_datetime.strftime('%Y-%m-%d')}")
            print(f"   Time: {meeting_datetime.strftime('%I:%M %p')}")
            print(f"   Duration: {meeting['duration_minutes']} minutes")
            print(f"   Participants: {', '.join(meeting['participants'])}")
        
        print(f"\nTotal: {len(meetings_to_show)} meeting(s)")
    
    def reschedule_meeting(self):
        """Reschedule an existing meeting."""
        print("\n" + "="*50)
        print("RESCHEDULE A MEETING")
        print("="*50)
        
        # List scheduled meetings
        scheduled_meetings = {k: v for k, v in self.meetings.items() 
                            if v["status"] in ["scheduled", "rescheduled"]}
        
        if not scheduled_meetings:
            print("No scheduled meetings to reschedule.")
            return
        
        print("\nScheduled meetings:")
        for meeting_id, meeting in scheduled_meetings.items():
            meeting_datetime = datetime.fromisoformat(meeting["datetime"])
            status_display = f"[{meeting['status'].upper()}]"
            print(f"{meeting_id}: {status_display} {meeting['title']} - {meeting_datetime.strftime('%Y-%m-%d %I:%M %p')}")
        
        # Get meeting ID to reschedule
        while True:
            meeting_id = input("\nEnter meeting ID to reschedule (or 'cancel' to go back): ").strip()
            
            if meeting_id.lower() == 'cancel':
                return
            
            if meeting_id in scheduled_meetings:
                break
            print("Invalid meeting ID. Please try again.")
        
        meeting = self.meetings[meeting_id]
        print(f"\nRescheduling: {meeting['title']}")
        
        # Get new date and time
        while True:
            print("\nEnter new date and time:")
            date_str = input("Date (YYYY-MM-DD): ").strip()
            time_str = input("Time (HH:MM or HH:MM AM/PM): ").strip()
            
            new_datetime = self.validate_datetime(date_str, time_str)
            if new_datetime:
                break
        
        # Check for time conflicts (excluding this meeting)
        if self.check_time_conflict(new_datetime, meeting["duration_minutes"], exclude_id=meeting_id):
            print("\n  Warning: There's a time conflict with another meeting!")
            proceed = input("Do you want to reschedule anyway? (yes/no): ").strip().lower()
            if proceed != 'yes':
                print("Rescheduling cancelled.")
                return
        
        # Update meeting
        old_datetime = meeting["datetime"]
        meeting["datetime"] = new_datetime.isoformat()
        meeting["status"] = "rescheduled"
        meeting["last_updated"] = datetime.now().isoformat()
        self.save_meetings()
        
        print(f"\n✓ Meeting rescheduled successfully!")
        print(f"  From: {datetime.fromisoformat(old_datetime).strftime('%Y-%m-%d %I:%M %p')}")
        print(f"  To:   {new_datetime.strftime('%Y-%m-%d %I:%M %p')}")
        
        # Send email notifications if configured
        if self.email_config.get("sender_email") and self.email_config.get("sender_password"):
            send_emails = input("\nSend email notifications about rescheduling? (yes/no): ").strip().lower()
            if send_emails == 'yes':
                email_count = 0
                for participant in meeting["participants"]:
                    subject = f"Meeting Rescheduled: {meeting['title']}"
                    body = f"""Hello,

The following meeting has been rescheduled:

Title: {meeting['title']}
Old Date/Time: {datetime.fromisoformat(old_datetime).strftime('%B %d, %Y at %I:%M %p')}
New Date/Time: {new_datetime.strftime('%B %d, %Y at %I:%M %p')}
Duration: {meeting['duration_minutes']} minutes
Meeting ID: {meeting_id}

Please update your calendar.

Best regards,
Meeting Scheduler
"""
                    if self.send_email_notification(participant, subject, body):
                        email_count += 1
                
                print(f"\n✓ Sent {email_count} email notification(s)")
    
    def cancel_meeting(self):
        """Cancel an existing meeting."""
        print("\n" + "="*50)
        print("CANCEL A MEETING")
        print("="*50)
        
        # List scheduled meetings
        scheduled_meetings = {k: v for k, v in self.meetings.items() 
                            if v["status"] in ["scheduled", "rescheduled"]}
        
        if not scheduled_meetings:
            print("No meetings to cancel.")
            return
        
        print("\nScheduled meetings:")
        for meeting_id, meeting in scheduled_meetings.items():
            meeting_datetime = datetime.fromisoformat(meeting["datetime"])
            status_display = f"[{meeting['status'].upper()}]"
            print(f"{meeting_id}: {status_display} {meeting['title']} - {meeting_datetime.strftime('%Y-%m-%d %I:%M %p')}")
        
        # Get meeting ID to cancel
        while True:
            meeting_id = input("\nEnter meeting ID to cancel (or 'cancel' to go back): ").strip()
            
            if meeting_id.lower() == 'cancel':
                return
            
            if meeting_id in scheduled_meetings:
                break
            print("Invalid meeting ID. Please try again.")
        
        meeting = self.meetings[meeting_id]
        
        # Confirm cancellation
        confirm = input(f"\nAre you sure you want to cancel '{meeting['title']}'? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Cancellation aborted.")
            return
        
        # Update meeting status
        meeting["status"] = "cancelled"
        meeting["cancelled_at"] = datetime.now().isoformat()
        self.save_meetings()
        
        print(f"\n✓ Meeting cancelled successfully!")
        
        # Send email notifications if configured
        if self.email_config.get("sender_email") and self.email_config.get("sender_password"):
            send_emails = input("\nSend email notifications about cancellation? (yes/no): ").strip().lower()
            if send_emails == 'yes':
                email_count = 0
                for participant in meeting["participants"]:
                    subject = f"Meeting Cancelled: {meeting['title']}"
                    body = f"""Hello,

The following meeting has been cancelled:

Title: {meeting['title']}
Originally scheduled for: {datetime.fromisoformat(meeting['datetime']).strftime('%B %d, %Y at %I:%M %p')}
Meeting ID: {meeting_id}

Please update your calendar.

Best regards,
Meeting Scheduler
"""
                    if self.send_email_notification(participant, subject, body):
                        email_count += 1
                
                print(f"\n✓ Sent {email_count} email notification(s)")
    
    def configure_email(self):
        """Configure email settings securely."""
        print("\n" + "="*50)
        print("CONFIGURE EMAIL SETTINGS")
        print("="*50)
        
        print("\n Email Configuration Guide:")
        print("-" * 40)
        print("1. For Gmail: Use App Password (recommended)")
        print("   • Enable 2-Factor Authentication")
        print("   • Generate App Password at:")
        print("     https://myaccount.google.com/apppasswords")
        print("2. Other providers: Check their SMTP settings")
        print("-" * 40)
        
        print("\nCurrent configuration:")
        for key, value in self.email_config.items():
            if key == "sender_password" and value:
                print(f"  {key}: {'*' * 8} (hidden)")
            else:
                print(f"  {key}: {value}")
        
        print("\nEnter new values (press Enter to keep current):")
        
        # Get SMTP server
        smtp_server = input(f"\nSMTP Server [{self.email_config['smtp_server']}]: ").strip()
        if smtp_server:
            self.email_config['smtp_server'] = smtp_server
        
        # Get SMTP port
        smtp_port = input(f"SMTP Port [{self.email_config['smtp_port']}]: ").strip()
        if smtp_port:
            try:
                self.email_config['smtp_port'] = int(smtp_port)
            except ValueError:
                print("Invalid port number. Keeping current value.")
        
        # Get sender email
        while True:
            sender_email = input(f"Sender Email [{self.email_config['sender_email']}]: ").strip()
            if not sender_email:
                break
            if self.validate_email(sender_email):
                self.email_config['sender_email'] = sender_email
                break
            print("Invalid email format. Please try again.")
        
        # Get sender password
        sender_password = input("Sender Password (leave empty to keep current): ").strip()
        if sender_password:
            self.email_config['sender_password'] = sender_password
        
        # Get TLS setting
        use_tls_input = input(f"Use TLS? (yes/no) [{'yes' if self.email_config.get('use_tls', True) else 'no'}]: ").strip().lower()
        if use_tls_input:
            self.email_config['use_tls'] = use_tls_input in ["yes", "y", "true", "t", "1"]
        
        # Save configuration locally
        self.save_configuration()
        print("\n✓ Email configuration updated and saved locally!")
        
        # Test email configuration
        if self.email_config["sender_email"] and self.email_config["sender_password"]:
            test_email = input("\nTest email configuration? (yes/no): ").strip().lower()
            if test_email == 'yes':
                test_recipient = input("Test recipient email: ").strip()
                if self.validate_email(test_recipient):
                    subject = "Meeting Scheduler - Test Email"
                    body = "This is a test email from the Meeting Scheduler application.\n\nIf you received this, your email configuration is working correctly!"
                    self.send_email_notification(test_recipient, subject, body)
                else:
                    print("Invalid email address. Test cancelled.")
        else:
            print("\n Email configuration incomplete. Email features will not work.")
    
    def search_meetings(self):
        """Search meetings by title or participant."""
        print("\n" + "="*50)
        print("SEARCH MEETINGS")
        print("="*50)
        
        search_term = input("Search by title or participant email: ").strip().lower()
        
        if not search_term:
            print("Search term cannot be empty.")
            return
        
        results = {}
        for meeting_id, meeting in self.meetings.items():
            # Search in title
            if search_term in meeting["title"].lower():
                results[meeting_id] = meeting
                continue
            
            # Search in participants
            for participant in meeting["participants"]:
                if search_term in participant.lower():
                    results[meeting_id] = meeting
                    break
        
        if not results:
            print(f"No meetings found matching '{search_term}'.")
            return
        
        print(f"\nFound {len(results)} meeting(s) matching '{search_term}':")
        
        # Sort by date
        sorted_results = sorted(
            results.items(),
            key=lambda x: datetime.fromisoformat(x[1]["datetime"])
        )
        
        for meeting_id, meeting in sorted_results:
            meeting_datetime = datetime.fromisoformat(meeting["datetime"])
            status_emoji = {
                "scheduled": "Y",
                "rescheduled": "R",
                "cancelled": "X"
            }.get(meeting['status'], '?')
            
            print(f"\n{status_emoji} [{meeting['status'].upper()}] ID: {meeting_id}")
            print(f"  Title: {meeting['title']}")
            print(f"  Date: {meeting_datetime.strftime('%Y-%m-%d')}")
            print(f"  Time: {meeting_datetime.strftime('%I:%M %p')}")
            print(f"  Participants: {', '.join(meeting['participants'])}")
    
    def display_upcoming_meetings(self):
        """Display upcoming meetings (next 7 days)."""
        print("\n" + "="*50)
        print("UPCOMING MEETINGS (Next 7 Days)")
        print("="*50)
        
        now = datetime.now()
        next_week = now + timedelta(days=7)
        
        upcoming = {}
        for meeting_id, meeting in self.meetings.items():
            if meeting["status"] not in ["scheduled", "rescheduled"]:
                continue
            
            meeting_datetime = datetime.fromisoformat(meeting["datetime"])
            if now <= meeting_datetime <= next_week:
                upcoming[meeting_id] = meeting
        
        if not upcoming:
            print("No upcoming meetings in the next 7 days.")
            return
        
        # Sort by date
        sorted_upcoming = sorted(
            upcoming.items(),
            key=lambda x: datetime.fromisoformat(x[1]["datetime"])
        )
        
        for meeting_id, meeting in sorted_upcoming:
            meeting_datetime = datetime.fromisoformat(meeting["datetime"])
            days_until = (meeting_datetime.date() - now.date()).days
            time_until = meeting_datetime - now
            
            # Status indicator
            if days_until == 0:
                time_indicator = "Today"
            elif days_until == 1:
                time_indicator = "Tomorrow"
            else:
                time_indicator = f" In {days_until} days"
            
            print(f"\n{time_indicator} - ID: {meeting_id}")
            print(f"  Title: {meeting['title']}")
            print(f"  Date: {meeting_datetime.strftime('%Y-%m-%d')}")
            print(f"  Time: {meeting_datetime.strftime('%I:%M %p')}")
            print(f"  Duration: {meeting['duration_minutes']} minutes")
            print(f"  Participants: {', '.join(meeting['participants'][:3])}")
            if len(meeting['participants']) > 3:
                print(f"    + {len(meeting['participants']) - 3} more")
    
    def display_menu(self):
        """Display the main menu."""
        print("\n" + "="*50)
        print(" MEETING SCHEDULER")
        print("="*50)
        print("1. Schedule a new meeting")
        print("2. List all meetings")
        print("3. List scheduled meetings")
        print("4. Reschedule a meeting")
        print("5. Cancel a meeting")
        print("6. Search meetings")
        print("7. View upcoming meetings (next 7 days)")
        print("8. Configure email settings")
        print("9. Exit")
        
        # Show email status
        email_status = "Configured" if (self.email_config.get("sender_email") and 
                                         self.email_config.get("sender_password")) else "⚠️  Not configured"
        print(f"\nEmail: {email_status}")
        print("="*50)
    
    def run(self):
        """Run the main application loop."""
        print("\n" + "="*50)
        print(" WELCOME TO MEETING SCHEDULER")
        print("="*50)
        print("A secure command-line application for managing meetings")
        print("\n  Configuration loaded from:")
        print(f"   • Environment variables")
        print(f"   • Local config: {CONFIG_FILE}")
        print(f"   • Meetings data: {MEETINGS_FILE}")
        
        while self.running:
            self.display_menu()
            
            try:
                choice = input("\nEnter your choice (1-9): ").strip()
                
                if choice == '1':
                    self.schedule_meeting()
                elif choice == '2':
                    self.list_meetings()
                elif choice == '3':
                    self.list_meetings(filter_status="scheduled")
                elif choice == '4':
                    self.reschedule_meeting()
                elif choice == '5':
                    self.cancel_meeting()
                elif choice == '6':
                    self.search_meetings()
                elif choice == '7':
                    self.display_upcoming_meetings()
                elif choice == '8':
                    self.configure_email()
                elif choice == '9':
                    print("\n" + "="*50)
                    print("Thank you for using Meeting Scheduler!")
                    print(f"Your data is saved in '{USER_DATA_DIR}/'")
                    print("="*50)
                    self.running = False
                else:
                    print("Invalid choice. Please enter a number between 1 and 9.")
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted by user. Saving data...")
                self.save_meetings()
                print("✓ Data saved. Goodbye!")
                self.running = False
            except Exception as e:
                print(f"\nAn unexpected error occurred: {e}")
                print("Please try again.")

def main():
    """Main entry point for the application."""
    scheduler = MeetingScheduler()
    scheduler.run()

if __name__ == "__main__":
    main()