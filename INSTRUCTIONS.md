## Usage
To use the website, you will first need to login to your Google account and grant permission to edit/add events to your calendar (no viruses, I promise :D).
**Interface & File Support**
* On the left column will be the upcoming events that the website found in your calendar, which you can mass select to mass delete (Not sure what else to use mass select for).
* Currently, the website only supports uploading PDF, I will add the feature for uploading .docx (.jpg and .png, too if possible) soon enough.
* A session lasts for 1 hour. Previously, if the session expires, the website fails and doesn't load anything. Now, it logs the user out and they have to login again. Currently, this is the only way and users have to log back in every hour.
### Reminder Settings
For each event type (exam or assignments, for example), you can input reminders to apply to them:
* **Custom Reminders:** For example, you add 2 reminders: 1 hour and 2 hours before exam. The website will add said event with those specific reminders to your calendar.
* **Event Types:** Each type of event have their own default reminder, so you can set them for each type.
* **Constraints:**
* The maximum value for reminder input is **40320 minutes** (4 weeks) because it's the maximum value allowed by Google Calendar.
* If no reminder is specified, it automatically uses the default reminder from Google Calendar (30 minutes before the event).