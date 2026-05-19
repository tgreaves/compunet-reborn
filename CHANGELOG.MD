# 0.2-beta (2026-05-19)

* Client:
	* Phone number input now accepts up to 24 characters (was 16).
	* Phone number input now accepts letters, allowing domain name entry.
	* Domain names are automatically lowercased when sent over the wire.
* Website:
	* Admin panel: View all registered users and pending registrations.
	* Admin panel: Edit user password, credit, name, email, and account type.
	* Admin panel: Approve or delete pending registrations.
	* Login now properly verifies passwords via server API.
	* Config now finds .env in project root when running locally (not just Docker).
	* Added animated walkthrough GIF to home page.
	* Connect page: added D64 download link, updated server address.
* Server:
	* New /api/auth endpoint for credential verification.
	* New /api/pending list endpoint for admin use.
	* /api/users update endpoint now supports credit and email changes.
	* Email address now stored when user accounts are created.
	* Fixed unhandled exception on client disconnect (connection reset).
	* Removed plaintext passwords from log output.
* Dev:
	* users.json removed from git tracking (use users.json.example for dev setup).
	* README: added Live Service section linking to https://compunet.live/
	* Docs: clarified that any number can be entered at the phone number prompt.

# 0.1-beta (2026-05-19)

First release.
