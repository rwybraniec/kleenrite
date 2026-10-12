"""Connector registry."""

from integrator.connectors.aws import S3, SQS
from integrator.connectors.netsuite import NetSuite
from integrator.errors import ConfigError

CONNECTORS = {"netsuite": NetSuite, "aws_s3": S3, "aws_sqs": SQS}


def build(config: dict, transport=None):
    try:
        cls = CONNECTORS[config["type"]]
    except KeyError:
        raise ConfigError(f"unknown connector type '{config['type']}'; "
                          f"available: {', '.join(sorted(CONNECTORS))}") from None
    return cls(config, transport)
