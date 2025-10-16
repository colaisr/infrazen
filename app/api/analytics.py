"""
Analytics API endpoints for dashboard data
"""
from flask import Blueprint, request, jsonify, session
from datetime import datetime, timedelta

from app.core.services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/api/analytics/summary', methods=['GET'])
def get_executive_summary():
    """Get executive summary KPIs"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        summary = analytics_service.get_executive_summary()
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/main-trends', methods=['GET'])
def get_main_trends():
    """Get main spending trends for primary chart"""
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        # Get parameters
        days = request.args.get('days', 30, type=int)
        provider = request.args.get('provider', None)
        
        # Get chart data
        trends_data = analytics_service.get_main_spending_trends(days)
        
        # Format data for Chart.js
        chart_data = {
            'labels': [item['date'] for item in trends_data],
            'datasets': [{
                'label': 'Общие расходы',
                'data': [item['total_cost'] for item in trends_data],
                'borderColor': '#1e40af',
                'backgroundColor': 'rgba(30, 64, 175, 0.1)',
                'tension': 0.4,
                'fill': True
            }]
        }
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/service-breakdown', methods=['GET'])
def get_service_breakdown():
    """Get service analysis for bar chart"""
    try:
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        service_data = analytics_service.get_service_analysis()
        
        # Format data for Chart.js bar chart
        chart_data = {
            'labels': [service['name'] for service in service_data['services']],
            'datasets': [{
                'label': 'Стоимость (₽/день)',
                'data': [service['cost'] for service in service_data['services']],
                'backgroundColor': ['#1e40af', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
            }]
        }
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/provider-breakdown', methods=['GET'])
def get_provider_breakdown():
    """Get provider breakdown for pie chart"""
    try:
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        provider_data = analytics_service.get_provider_breakdown()
        
        # Format data for Chart.js doughnut chart
        chart_data = {
            'labels': [provider['name'] for provider in provider_data['providers']],
            'datasets': [{
                'label': 'Стоимость (₽/день)',
                'data': [provider['cost'] for provider in provider_data['providers']],
                'backgroundColor': ['#1e40af', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
            }]
        }
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/provider-trends/<int:provider_id>', methods=['GET'])
def get_provider_trends(provider_id):
    """Get individual provider spending trends"""
    try:
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        # Get parameters
        days = request.args.get('days', 30, type=int)
        
        trends_data = analytics_service.get_provider_trends(provider_id, days)
        
        # Format data for Chart.js line chart
        chart_data = {
            'labels': [item['date'] for item in trends_data],
            'datasets': [{
                'label': f'Расходы провайдера {provider_id}',
                'data': [item['total_cost'] for item in trends_data],
                'borderColor': '#10b981',
                'backgroundColor': 'rgba(16, 185, 129, 0.1)',
                'tension': 0.4,
                'fill': True
            }]
        }
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/implemented-recommendations', methods=['GET'])
def get_implemented_recommendations():
    """Get implemented recommendations"""
    try:
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        recommendations = analytics_service.get_implemented_recommendations()
        
        return jsonify({
            'success': True,
            'data': recommendations
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/optimization-opportunities', methods=['GET'])
def get_optimization_opportunities():
    """Get pending optimization opportunities"""
    try:
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        opportunities = analytics_service.get_optimization_opportunities()
        
        return jsonify({
            'success': True,
            'data': opportunities
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/export', methods=['POST'])
def export_analytics_report():
    """Export analytics report"""
    try:
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        # Get export parameters
        data = request.get_json()
        format_type = data.get('format', 'pdf')
        
        # Generate report
        report_data = analytics_service.export_analytics_report(format_type)
        
        return jsonify({
            'success': True,
            'data': {
                'format': format_type,
                'download_url': f'/api/analytics/download/{format_type}',
                'message': f'Report generated in {format_type.upper()} format'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/api/analytics/download/<format_type>', methods=['GET'])
def download_report(format_type):
    """Download generated report"""
    try:
        user_id = int(float(session['user']['id']))
        analytics_service = AnalyticsService(user_id)
        
        # Generate and return report
        report_data = analytics_service.export_analytics_report(format_type)
        
        # Set appropriate headers
        if format_type == 'pdf':
            return report_data, 200, {
                'Content-Type': 'application/pdf',
                'Content-Disposition': f'attachment; filename=analytics_report_{datetime.now().strftime("%Y%m%d")}.pdf'
            }
        elif format_type == 'excel':
            return report_data, 200, {
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'Content-Disposition': f'attachment; filename=analytics_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
            }
        elif format_type == 'csv':
            return report_data, 200, {
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename=analytics_report_{datetime.now().strftime("%Y%m%d")}.csv'
            }
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
