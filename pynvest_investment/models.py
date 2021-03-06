from django.db import models
import django.db.backends.signals
import datetime
import math

from . import managers

@django.dispatch.receiver(django.db.backends.signals.connection_created)
def add_sqlite_math_functions(connection, **kwargs):
    if connection.vendor != 'sqlite':
        return

    connection.connection.create_function('ln', 1, math.log)
    connection.connection.create_function('exp', 1, math.exp)


class Exchange(models.Model):
    symbol          = models.CharField(max_length=10, unique=True)
    name            = models.CharField(max_length=200)

    def __unicode__(self):
        return u'%s' % self.symbol


class Investment(models.Model):
    exchange        = models.ForeignKey(Exchange)
    symbol          = models.CharField(max_length=10, unique=True)
    name            = models.CharField(max_length=200)

    def __unicode__(self):
        return u'%s' % (self.symbol)

    def current_price(self):
        return self.snapshot_set.latest('date').close

    def _year_data(self, field):
        if not hasattr(self, '_year_data_cache'):
            self._year_data_cache = self.snapshot_set.filter_year_range().aggregate(high=models.Max('high'), low=models.Min('low'))
        return self._year_data_cache[field]

    def year_high(self):
        return self._year_data('high')

    def year_low(self):
        return self._year_data('low')


class Snapshot(models.Model):
    investment      = models.ForeignKey(Investment)
    date            = models.DateField(db_index=True)
    high            = models.DecimalField(max_digits=12, decimal_places=4)
    low             = models.DecimalField(max_digits=12, decimal_places=4)
    close           = models.DecimalField(max_digits=12, decimal_places=4)
    dividend        = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    split_before    = models.IntegerField(default=1)
    split_after     = models.IntegerField(default=1)

    class Meta:
        unique_together = [('investment', 'date')]

    def dividend_percent(self):
        return self.dividend / self.close

    def split(self):
        if self.split_before == 1 and self.split_after == 1:
            return ''

        return '%d:%d' % (self.split_after, self.split_before)

    objects = managers.QuerySetManager()
    class QuerySet(models.query.QuerySet):
        def filter_year_range(self, end_date=None):
            end_date = end_date or datetime.date.today()
            start_date = end_date - datetime.timedelta(days=365)
            return self.filter(date__lte=end_date, date__gte=start_date)

        def close_adjusted(self):
            aggr_func = 'SUM(LN(1.0 * close / (close + dividend) * split_before / split_after))'
            subquery = '''SELECT %(table)s.close * EXP(COALESCE(%(aggr_func)s, 0))
                            FROM %(table)s t
                           WHERE investment_id = %(table)s.investment_id
                             AND (dividend > 0 OR split_before != 1 OR split_after != 1)
                             AND date > %(table)s.date
                       ''' % {'table': self.model._meta.db_table, 'aggr_func': aggr_func}
            return self.extra(select={'close_adjusted': subquery})
