from tastypie.resources import ModelResource
from tastypie import fields
from metadata.models import Reporter, Article


class ReporterResource(ModelResource):
    class Meta:
        queryset = Reporter.objects.all()
        resource_name = 'reporter'
        excludes = ['starts_at', 'ends_at']


class ArticleResource(ModelResource):
    reporter = fields.ForeignKey(ReporterResource, 'reporter')

    class Meta:
        queryset = Article.objects.all()
        resource_name = 'article'