from django import forms

class ColorPickerWidget(forms.TextInput):
    """
    Simple color picker widget for Django admin
    """
    input_type = 'color'
    
    def __init__(self, attrs=None):
        default_attrs = {'style': 'width: 60px; height: 40px; border: none; cursor: pointer;'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
