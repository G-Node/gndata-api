from tastypie.resources import ModelResource, ALL
from tastypie import fields
from tastypie.authentication import SessionAuthentication

from rest.authorization import BaseAuthorization
from metadata.models import Reporter, Article


class ReporterResource(ModelResource):
    class Meta:
        queryset = Reporter.objects.all()
        resource_name = 'reporter'
        excludes = ['starts_at', 'ends_at']
        filtering = {
            'first_name': ALL
        }
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()


class ArticleResource(ModelResource):
    reporter = fields.ForeignKey(ReporterResource, 'reporter')

    class Meta:
        queryset = Article.objects.all()
        resource_name = 'article'
        authentication = SessionAuthentication()
        authorization = BaseAuthorization()