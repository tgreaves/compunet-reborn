# 0.2-beta (2026-05-19)

* Website:
	* Admin panel: View all registered users and pending registrations.
	* Admin panel: Edit user password, credit, name, and account type.
	* Admin panel: Approve or delete pending registrations.
	* Login now properly verifies passwords via server API.
	* Config now finds .env in project root when running locally (not just Docker).
	* Added animated walkthrough GIF to home page.
	* Connect page: added D64 download link, updated server address.
* Server:
	* New /api/auth endpoint for credential verification.
	* New /api/pending list endpoint for admin use.
	* /api/users update endpoint now supports credit changes.
* Dev:
	* users.json removed from git tracking (use users.json.example for dev setup).

# 0.1-beta (2026-05-19)

First release.
