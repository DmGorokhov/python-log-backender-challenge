from enum import Enum


class ChoiceEnum(Enum):
    def __repr__(self) -> str:
        return f"{self.value}"

    def __str__(self) -> str:
        return f"{self.value}"

    @classmethod
    def item_to_index(cls, index: int) -> list:
        return list(cls)[index]

    @classmethod
    def choices(cls) -> list:
        return [(i, i.value) for i in cls]

    @classmethod
    def choices_with_name(cls) -> list:
        return [(i.name, i.value) for i in cls]

    @classmethod
    def choices_with_index(cls) -> list:
        return list(enumerate(cls))

    @classmethod
    def find(cls, value): # noqa
        result = list(filter(lambda i: value == i.value, cls))
        return result[0] if result else cls


class EvenLogStatus(str, ChoiceEnum):
    AWAITING_DELIVER = "AWAITING_DELIVER"
    SENDING = "SENDING"
    DELIVERED = "DELIVERED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
