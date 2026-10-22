from django.db.migrations import AddIndex


class AddPostgresIndex(AddIndex):
    """AddIndex for Postgres-only index types (GIN and friends).

    The model state is updated everywhere so `makemigrations` stays consistent; the SQL
    runs only on Postgres, so the SQLite test escape hatch can still migrate.
    """

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if schema_editor.connection.vendor == "postgresql":
            super().database_backwards(app_label, schema_editor, from_state, to_state)
