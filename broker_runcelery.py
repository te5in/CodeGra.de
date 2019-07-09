import cg_broker

app = cg_broker.create_app()
celery = cg_broker.tasks.celery
