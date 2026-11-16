"""Serializable observations for production AOT capture of the MTP fixture."""
from dataclasses import fields


class ProjectionObservation:
    def __init__(self, operation, stages):
        self.operation, self.stages = operation, stages

    def __call__(self, source):
        self.stages['joined'].copy_(source)
        value = self.operation(source)
        self.stages['feedback_projection'].copy_(value)
        return value


class OutputObservation:
    def __init__(self, operation, output):
        self.operation, self.output = operation, output

    def __call__(self, source):
        value = self.operation(source)
        self.output.copy_(value)
        return value


class InputObservation:
    def __init__(self, operation, output):
        self.operation, self.output = operation, output

    def __call__(self, source):
        self.output.copy_(source)
        return self.operation(source)


class SelectionObservation:
    def __init__(self, operation, storage):
        self.operation, self.storage = operation, storage

    def __call__(self, *args, **kwargs):
        selection, scratch = self.operation(*args, **kwargs)
        for field in fields(self.storage):
            getattr(self.storage, field.name).copy_(getattr(scratch, field.name))
        return selection, scratch


class MTPReplayForward:
    def __init__(self, operation, metadata, cache_only, output, stages):
        self.operation, self.metadata = operation, metadata
        self.cache_only, self.output, self.stages = cache_only, output, stages

    def __call__(self):
        result = self.operation(self.metadata)
        if self.cache_only:
            self.output.copy_(self.metadata.hidden)
        else:
            self.output.copy_(result[0])
            self.stages['logits'].copy_(result[1])
