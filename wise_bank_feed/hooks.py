app_name = "wise_bank_feed"
app_title = "Wise Bank Feed"
app_publisher = "Wise Bank Feed contributors"
app_description = "Read-only Wise activity and statement feed"
app_email = ""
app_license = "MIT"
required_apps = ["erpnext"]
app_home = "/desk/wise-setup"
app_logo_url = "/assets/wise_bank_feed/bank.svg"
add_to_apps_screen = [
    dict(
        name=app_name,
        title=app_title,
        logo=app_logo_url,
        route=app_home,
        has_permission="wise_bank_feed.api.has_permission",
    )
]
before_install = "wise_bank_feed.install.check_versions"
after_install = "wise_bank_feed.install.after_migrate"
after_migrate = "wise_bank_feed.install.after_migrate"
before_uninstall = "wise_bank_feed.install.before_uninstall"
scheduler_events = {"cron": {"*/15 * * * *": ["wise_bank_feed.sync.schedule"]}}
doc_events = {
    "Bank Transaction": {
        "validate": "wise_bank_feed.guards.validate",
        "before_update_after_submit": "wise_bank_feed.guards.validate",
        "before_cancel": "wise_bank_feed.guards.before_cancel",
        "on_trash": "wise_bank_feed.guards.before_delete",
    }
}
