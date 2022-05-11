from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea, required=True)

    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': 'Автор',
            'group': 'Название группы',
            'image': 'Картинка для поста',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст комментария',
        }
