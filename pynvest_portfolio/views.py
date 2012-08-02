from django.shortcuts import render_to_response, get_object_or_404
from . import models, presenters, util


def portfolio_summary(request, id):
    portfolio = get_object_or_404(models.Portfolio, id=id)
    lots = models.Lot.objects.filter(portfolio=portfolio, outstanding_shares__gt=0)
    return render_to_response('pynvest_portfolio/lot_summary_table.html', {
        'title': portfolio.name,
        'lot_summarys': presenters.LotSummary.group_by_investment(lots),
    })


def portfolio_growth(request, id):
    portfolio = get_object_or_404(models.Portfolio, id=id)
    return render_to_response('pynvest_core/growths_table.html', {
        'title': portfolio.name,
        'growths': [presenters.PortfolioGrowth(portfolio)],
    })


def portfolio_sales(request, id, year):
    portfolio = get_object_or_404(models.Portfolio, id=id)
    transactions = models.Transaction.objects.filter(lot__portfolio=portfolio, date__year=year)\
                                             .order_by('date', 'lot__investment')

    return render_to_response('pynvest_portfolio/transaction_sales_table.html', {
        'title': portfolio.name,
        'transactions': [t for t in transactions if t.base_transaction() != t],
    })


def portfolio_flat(request, id):
    portfolio = get_object_or_404(models.Portfolio, id=id)
    return render_to_response('pynvest_portfolio/transactions.html', {
        'portfolio': portfolio,
        'transactions': models.Transaction.objects.filter(lot__portfolio=portfolio).order_by('date', 'lot__investment'),
    })
