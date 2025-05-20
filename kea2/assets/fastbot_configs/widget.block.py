from kea2.utils import precondition
from uiautomator2 import Device


@precondition(lambda d:
    d(text="Setting")
)
def sample_block_list(d: "Device"):
    return d(text="Omni Notes Alpha").exists


if __name__ == "__main__":
    from kea2.utils import BLOCK_WIDGET
    func = getattr(sample_block_list, BLOCK_WIDGET)
    import uiautomator2 as u2
    d = u2.connect()
    blocked_widgets = func(d)
    if isinstance(blocked_widgets, u2.UiObject):
        blocked_widgets = [blocked_widgets]
    if not all([isinstance(w, u2.UiObject) for w in blocked_widgets]):
        raise TypeError(f"Invalid widgets block list in {sample_block_list}")
    