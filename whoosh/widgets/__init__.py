from whoosh.widgets.audio import AudioPlayerWidget
from whoosh.widgets.dict_tree import ObjectDictTreeWidget
from whoosh.widgets.generic import GenericObjectView
from whoosh.widgets.movie import MoviePlayerWidget
from whoosh.widgets.text_repr import ObjectTextReprWidget
from whoosh.widgets.texture import TextureViewWidget

__all__ = [
    "AudioPlayerWidget",
    "GenericObjectView",
    "MoviePlayerWidget",
    "ObjectDictTreeWidget",
    "ObjectTextReprWidget",
    "TextureViewWidget",
    "widget_for_object",
]

_WIDGET_BY_CLASS_ID = {
    28: TextureViewWidget,
    83: AudioPlayerWidget,
    152: MoviePlayerWidget,
}


def widget_for_object(obj):
    """Return the appropriate widget for a unitypack object."""
    class_id = getattr(obj, "class_id", None)
    widget_cls = _WIDGET_BY_CLASS_ID.get(class_id, GenericObjectView)
    return widget_cls(obj)
