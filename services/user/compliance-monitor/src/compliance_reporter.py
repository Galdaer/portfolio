#!/usr/bin/env python3
"""
Compliance Reporter

Generates compliance reports, dashboards, and automated notifications
for HIPAA and healthcare regulatory requirements.
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from jinja2 import Template
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

from models.compliance_models import (
    ViolationType, ViolationSeverity, ViolationStatus,
    ComplianceViolation
)

logger = logging.getLogger(__name__)

class ReportType(Enum):
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_COMPLIANCE = "weekly_compliance"
    MONTHLY_AUDIT = "monthly_audit"
    VIOLATION_ANALYSIS = "violation_analysis"
    USER_ACTIVITY = "user_activity"
    RISK_ASSESSMENT = "risk_assessment"
    REGULATORY_SUMMARY = "regulatory_summary"

class ReportFormat(Enum):
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    CSV = "csv"

@dataclass
class ReportRequest:
    """Request for generating a compliance report"""
    report_type: ReportType
    format: ReportFormat = ReportFormat.HTML
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[str] = None
    service_name: Optional[str] = None
    severity_filter: Optional[ViolationSeverity] = None
    include_resolved: bool = True
    
class ComplianceReporter:
    """Generates compliance reports and visualizations"""
    
    def __init__(self, 
                 db_host: str = "localhost",
                 db_port: int = 5432,
                 db_name: str = "intelluxe_public",
                 db_user: str = "intelluxe",
                 db_password: str = "secure_password"):
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        
        # Configure matplotlib for non-interactive backend
        plt.switch_backend('Agg')
        sns.set_style("whitegrid")
        
    async def generate_report(self, request: ReportRequest) -> Dict[str, Any]:
        """Generate a compliance report based on the request"""
        try:
            # Set default date range if not provided
            if not request.end_date:
                request.end_date = datetime.now()
            if not request.start_date:
                if request.report_type == ReportType.DAILY_SUMMARY:
                    request.start_date = request.end_date - timedelta(days=1)
                elif request.report_type == ReportType.WEEKLY_COMPLIANCE:
                    request.start_date = request.end_date - timedelta(days=7)
                elif request.report_type == ReportType.MONTHLY_AUDIT:
                    request.start_date = request.end_date - timedelta(days=30)
                else:
                    request.start_date = request.end_date - timedelta(days=7)
            
            # Get data based on report type
            report_data = await self._get_report_data(request)
            
            # Generate visualizations
            charts = await self._generate_charts(report_data, request)
            
            # Format the report
            formatted_report = await self._format_report(report_data, charts, request)
            
            return {
                "report_id": f"{request.report_type.value}_{int(datetime.now().timestamp())}",
                "report_type": request.report_type.value,
                "format": request.format.value,
                "generated_at": datetime.now().isoformat(),
                "date_range": {
                    "start": request.start_date.isoformat(),
                    "end": request.end_date.isoformat()
                },
                "data": report_data,
                "charts": charts,
                "formatted_output": formatted_report
            }
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            raise
    
    async def _get_report_data(self, request: ReportRequest) -> Dict[str, Any]:
        """Get data for the requested report"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            
            data = {}
            
            if request.report_type == ReportType.DAILY_SUMMARY:
                data = await self._get_daily_summary_data(conn, request)
            elif request.report_type == ReportType.WEEKLY_COMPLIANCE:
                data = await self._get_weekly_compliance_data(conn, request)
            elif request.report_type == ReportType.MONTHLY_AUDIT:
                data = await self._get_monthly_audit_data(conn, request)
            elif request.report_type == ReportType.VIOLATION_ANALYSIS:
                data = await self._get_violation_analysis_data(conn, request)
            elif request.report_type == ReportType.USER_ACTIVITY:
                data = await self._get_user_activity_data(conn, request)
            elif request.report_type == ReportType.RISK_ASSESSMENT:
                data = await self._get_risk_assessment_data(conn, request)
            elif request.report_type == ReportType.REGULATORY_SUMMARY:
                data = await self._get_regulatory_summary_data(conn, request)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to get report data: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def _get_daily_summary_data(self, conn, request: ReportRequest) -> Dict[str, Any]:
        """Get data for daily summary report"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total violations today
            cur.execute("""
                SELECT COUNT(*) as total_violations,
                       COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
                       COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
                       COUNT(CASE WHEN severity = 'medium' THEN 1 END) as medium,
                       COUNT(CASE WHEN severity = 'low' THEN 1 END) as low
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
            """, (request.start_date, request.end_date))
            violation_counts = dict(cur.fetchone())
            
            # Top violated rules today
            cur.execute("""
                SELECT rule_id, COUNT(*) as count
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                GROUP BY rule_id
                ORDER BY count DESC
                LIMIT 5
            """, (request.start_date, request.end_date))
            top_rules = [dict(row) for row in cur.fetchall()]
            
            # Recent critical violations
            cur.execute("""
                SELECT violation_id, rule_id, user_id, service_name, description,
                       first_detected_at, status
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                      AND severity = 'critical'
                ORDER BY first_detected_at DESC
                LIMIT 10
            """, (request.start_date, request.end_date))
            critical_violations = [dict(row) for row in cur.fetchall()]
            
            # Audit event summary
            cur.execute("""
                SELECT COUNT(*) as total_events,
                       COUNT(DISTINCT user_id) as unique_users,
                       COUNT(DISTINCT service_name) as active_services
                FROM audit_events
                WHERE timestamp >= %s AND timestamp < %s
            """, (request.start_date, request.end_date))
            audit_summary = dict(cur.fetchone())
            
            return {
                "summary_date": request.start_date.date().isoformat(),
                "violation_counts": violation_counts,
                "top_violated_rules": top_rules,
                "critical_violations": critical_violations,
                "audit_summary": audit_summary
            }
    
    async def _get_weekly_compliance_data(self, conn, request: ReportRequest) -> Dict[str, Any]:
        """Get data for weekly compliance report"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Daily violation trends
            cur.execute("""
                SELECT DATE(first_detected_at) as violation_date,
                       COUNT(*) as violations,
                       COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                GROUP BY DATE(first_detected_at)
                ORDER BY violation_date
            """, (request.start_date, request.end_date))
            daily_trends = [dict(row) for row in cur.fetchall()]
            
            # Service compliance scores
            cur.execute("""
                SELECT service_name,
                       COUNT(*) as total_violations,
                       COUNT(CASE WHEN severity IN ('critical', 'high') THEN 1 END) as high_severity
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                      AND service_name IS NOT NULL
                GROUP BY service_name
                ORDER BY total_violations DESC
            """, (request.start_date, request.end_date))
            service_scores = [dict(row) for row in cur.fetchall()]
            
            # User compliance metrics
            cur.execute("""
                SELECT user_id,
                       COUNT(*) as violations,
                       COUNT(DISTINCT rule_id) as different_violations,
                       MAX(first_detected_at) as latest_violation
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                      AND user_id IS NOT NULL
                GROUP BY user_id
                HAVING COUNT(*) > 1
                ORDER BY violations DESC
                LIMIT 10
            """, (request.start_date, request.end_date))
            user_metrics = [dict(row) for row in cur.fetchall()]
            
            return {
                "week_start": request.start_date.date().isoformat(),
                "week_end": request.end_date.date().isoformat(),
                "daily_trends": daily_trends,
                "service_compliance_scores": service_scores,
                "user_compliance_metrics": user_metrics
            }
    
    async def _get_monthly_audit_data(self, conn, request: ReportRequest) -> Dict[str, Any]:
        """Get data for monthly audit report"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Monthly summary
            cur.execute("""
                SELECT COUNT(*) as total_violations,
                       COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                       COUNT(CASE WHEN status = 'open' THEN 1 END) as open,
                       AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, NOW()) - first_detected_at))/3600) as avg_resolution_hours
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
            """, (request.start_date, request.end_date))
            monthly_summary = dict(cur.fetchone())
            
            # Rule effectiveness analysis
            cur.execute("""
                SELECT rule_id,
                       COUNT(*) as violations,
                       COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                       AVG(CASE WHEN resolved_at IS NOT NULL THEN 
                           EXTRACT(EPOCH FROM (resolved_at - first_detected_at))/3600 
                           END) as avg_resolution_hours
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                GROUP BY rule_id
                ORDER BY violations DESC
            """, (request.start_date, request.end_date))
            rule_effectiveness = [dict(row) for row in cur.fetchall()]
            
            # Compliance trends by week
            cur.execute("""
                SELECT EXTRACT(WEEK FROM first_detected_at) as week_number,
                       COUNT(*) as violations,
                       COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                GROUP BY EXTRACT(WEEK FROM first_detected_at)
                ORDER BY week_number
            """, (request.start_date, request.end_date))
            weekly_trends = [dict(row) for row in cur.fetchall()]
            
            return {
                "month_start": request.start_date.date().isoformat(),
                "month_end": request.end_date.date().isoformat(),
                "monthly_summary": monthly_summary,
                "rule_effectiveness": rule_effectiveness,
                "weekly_trends": weekly_trends
            }
    
    async def _get_violation_analysis_data(self, conn, request: ReportRequest) -> Dict[str, Any]:
        """Get detailed violation analysis data"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Violation patterns
            cur.execute("""
                SELECT rule_id, 
                       COUNT(*) as frequency,
                       AVG(EXTRACT(EPOCH FROM (last_detected_at - first_detected_at))/60) as avg_duration_minutes,
                       COUNT(DISTINCT user_id) as affected_users
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                GROUP BY rule_id
                ORDER BY frequency DESC
            """, (request.start_date, request.end_date))
            violation_patterns = [dict(row) for row in cur.fetchall()]
            
            # Time-based analysis
            cur.execute("""
                SELECT EXTRACT(HOUR FROM first_detected_at) as hour_of_day,
                       COUNT(*) as violations
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                GROUP BY EXTRACT(HOUR FROM first_detected_at)
                ORDER BY hour_of_day
            """, (request.start_date, request.end_date))
            hourly_distribution = [dict(row) for row in cur.fetchall()]
            
            return {
                "analysis_period": f"{request.start_date.date()} to {request.end_date.date()}",
                "violation_patterns": violation_patterns,
                "hourly_distribution": hourly_distribution
            }
    
    async def _get_user_activity_data(self, conn, request: ReportRequest) -> Dict[str, Any]:
        """Get user activity analysis data"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # User violation summary
            cur.execute("""
                SELECT user_id,
                       COUNT(*) as total_violations,
                       COUNT(CASE WHEN severity = 'critical' THEN 1 END) as critical,
                       COUNT(CASE WHEN severity = 'high' THEN 1 END) as high,
                       MIN(first_detected_at) as first_violation,
                       MAX(first_detected_at) as latest_violation
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                      AND user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY total_violations DESC
            """, (request.start_date, request.end_date))
            user_summary = [dict(row) for row in cur.fetchall()]
            
            return {
                "activity_period": f"{request.start_date.date()} to {request.end_date.date()}",
                "user_violation_summary": user_summary
            }
    
    async def _get_risk_assessment_data(self, conn, request: ReportRequest) -> Dict[str, Any]:
        """Get risk assessment data"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Calculate risk scores by service
            cur.execute("""
                SELECT service_name,
                       COUNT(*) as violations,
                       SUM(CASE 
                           WHEN severity = 'critical' THEN 4
                           WHEN severity = 'high' THEN 3
                           WHEN severity = 'medium' THEN 2
                           WHEN severity = 'low' THEN 1
                           ELSE 0
                       END) as risk_score,
                       COUNT(CASE WHEN status = 'open' THEN 1 END) as open_violations
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                      AND service_name IS NOT NULL
                GROUP BY service_name
                ORDER BY risk_score DESC
            """, (request.start_date, request.end_date))
            service_risk_scores = [dict(row) for row in cur.fetchall()]
            
            # Risk trends
            cur.execute("""
                SELECT DATE(first_detected_at) as risk_date,
                       SUM(CASE 
                           WHEN severity = 'critical' THEN 4
                           WHEN severity = 'high' THEN 3
                           WHEN severity = 'medium' THEN 2
                           WHEN severity = 'low' THEN 1
                           ELSE 0
                       END) as daily_risk_score
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                GROUP BY DATE(first_detected_at)
                ORDER BY risk_date
            """, (request.start_date, request.end_date))
            risk_trends = [dict(row) for row in cur.fetchall()]
            
            return {
                "assessment_period": f"{request.start_date.date()} to {request.end_date.date()}",
                "service_risk_scores": service_risk_scores,
                "risk_trends": risk_trends
            }
    
    async def _get_regulatory_summary_data(self, conn, request: ReportRequest) -> Dict[str, Any]:
        """Get regulatory compliance summary data"""
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # HIPAA-specific violations
            cur.execute("""
                SELECT rule_id, COUNT(*) as violations,
                       COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
                      AND (rule_id LIKE '%phi%' OR rule_id LIKE '%hipaa%')
                GROUP BY rule_id
                ORDER BY violations DESC
            """, (request.start_date, request.end_date))
            hipaa_violations = [dict(row) for row in cur.fetchall()]
            
            # Compliance metrics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_violations,
                    COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved,
                    COUNT(CASE WHEN severity = 'critical' AND status = 'open' THEN 1 END) as critical_open,
                    AVG(CASE WHEN resolved_at IS NOT NULL THEN 
                        EXTRACT(EPOCH FROM (resolved_at - first_detected_at))/3600 
                        END) as avg_resolution_hours
                FROM compliance_violations
                WHERE first_detected_at >= %s AND first_detected_at < %s
            """, (request.start_date, request.end_date))
            compliance_metrics = dict(cur.fetchone())
            
            return {
                "regulatory_period": f"{request.start_date.date()} to {request.end_date.date()}",
                "hipaa_violations": hipaa_violations,
                "compliance_metrics": compliance_metrics
            }
    
    async def _generate_charts(self, data: Dict[str, Any], request: ReportRequest) -> Dict[str, str]:
        """Generate charts for the report"""
        charts = {}
        
        try:
            if request.report_type == ReportType.DAILY_SUMMARY:
                charts.update(await self._create_daily_charts(data))
            elif request.report_type == ReportType.WEEKLY_COMPLIANCE:
                charts.update(await self._create_weekly_charts(data))
            elif request.report_type == ReportType.MONTHLY_AUDIT:
                charts.update(await self._create_monthly_charts(data))
            elif request.report_type == ReportType.VIOLATION_ANALYSIS:
                charts.update(await self._create_analysis_charts(data))
            elif request.report_type == ReportType.RISK_ASSESSMENT:
                charts.update(await self._create_risk_charts(data))
                
        except Exception as e:
            logger.error(f"Failed to generate charts: {e}")
            
        return charts
    
    async def _create_daily_charts(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Create charts for daily summary report"""
        charts = {}
        
        # Violation severity pie chart
        if data.get("violation_counts"):
            counts = data["violation_counts"]
            severities = ['critical', 'high', 'medium', 'low']
            values = [counts.get(s, 0) for s in severities]
            
            if sum(values) > 0:
                fig, ax = plt.subplots(figsize=(8, 6))
                colors = ['#ff4444', '#ff8800', '#ffaa00', '#00aa00']
                ax.pie(values, labels=severities, colors=colors, autopct='%1.1f%%')
                ax.set_title('Daily Violations by Severity')
                
                charts['severity_distribution'] = self._fig_to_base64(fig)
                plt.close(fig)
        
        return charts
    
    async def _create_weekly_charts(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Create charts for weekly compliance report"""
        charts = {}
        
        # Daily trends line chart
        if data.get("daily_trends"):
            trends = data["daily_trends"]
            dates = [t['violation_date'] for t in trends]
            violations = [t['violations'] for t in trends]
            
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.plot(dates, violations, marker='o', linewidth=2)
            ax.set_title('Daily Violation Trends')
            ax.set_xlabel('Date')
            ax.set_ylabel('Number of Violations')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            charts['daily_trends'] = self._fig_to_base64(fig)
            plt.close(fig)
        
        return charts
    
    async def _create_monthly_charts(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Create charts for monthly audit report"""
        charts = {}
        
        # Rule effectiveness bar chart
        if data.get("rule_effectiveness"):
            rules = data["rule_effectiveness"][:10]  # Top 10
            rule_names = [r['rule_id'] for r in rules]
            violation_counts = [r['violations'] for r in rules]
            
            fig, ax = plt.subplots(figsize=(12, 8))
            bars = ax.barh(rule_names, violation_counts)
            ax.set_title('Top 10 Most Violated Rules')
            ax.set_xlabel('Number of Violations')
            
            # Color bars by count
            for i, bar in enumerate(bars):
                if violation_counts[i] >= 50:
                    bar.set_color('#ff4444')
                elif violation_counts[i] >= 20:
                    bar.set_color('#ff8800')
                else:
                    bar.set_color('#4444ff')
            
            plt.tight_layout()
            charts['rule_effectiveness'] = self._fig_to_base64(fig)
            plt.close(fig)
        
        return charts
    
    async def _create_analysis_charts(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Create charts for violation analysis report"""
        charts = {}
        
        # Hourly distribution heatmap
        if data.get("hourly_distribution"):
            hourly = data["hourly_distribution"]
            hours = [int(h['hour_of_day']) for h in hourly]
            violations = [h['violations'] for h in hourly]
            
            # Create 24-hour array
            hour_violations = [0] * 24
            for hour, count in zip(hours, violations):
                hour_violations[hour] = count
            
            fig, ax = plt.subplots(figsize=(12, 4))
            ax.bar(range(24), hour_violations, color='skyblue')
            ax.set_title('Violations by Hour of Day')
            ax.set_xlabel('Hour')
            ax.set_ylabel('Number of Violations')
            ax.set_xticks(range(0, 24, 2))
            
            charts['hourly_distribution'] = self._fig_to_base64(fig)
            plt.close(fig)
        
        return charts
    
    async def _create_risk_charts(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Create charts for risk assessment report"""
        charts = {}
        
        # Service risk scores
        if data.get("service_risk_scores"):
            services = data["service_risk_scores"][:10]
            service_names = [s['service_name'] for s in services]
            risk_scores = [s['risk_score'] for s in services]
            
            fig, ax = plt.subplots(figsize=(12, 8))
            bars = ax.barh(service_names, risk_scores)
            ax.set_title('Service Risk Scores')
            ax.set_xlabel('Risk Score')
            
            # Color by risk level
            for i, bar in enumerate(bars):
                if risk_scores[i] >= 100:
                    bar.set_color('#ff0000')
                elif risk_scores[i] >= 50:
                    bar.set_color('#ff8800')
                elif risk_scores[i] >= 20:
                    bar.set_color('#ffaa00')
                else:
                    bar.set_color('#00aa00')
            
            plt.tight_layout()
            charts['service_risk_scores'] = self._fig_to_base64(fig)
            plt.close(fig)
        
        return charts
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string"""
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        graphic = base64.b64encode(image_png).decode('utf-8')
        return graphic
    
    async def _format_report(self, data: Dict[str, Any], charts: Dict[str, str], request: ReportRequest) -> str:
        """Format the report based on the requested format"""
        if request.format == ReportFormat.JSON:
            return json.dumps({
                "data": data,
                "charts": charts
            }, indent=2, default=str)
        
        elif request.format == ReportFormat.HTML:
            return await self._generate_html_report(data, charts, request)
        
        elif request.format == ReportFormat.CSV:
            return await self._generate_csv_report(data, request)
        
        else:
            return json.dumps(data, indent=2, default=str)
    
    async def _generate_html_report(self, data: Dict[str, Any], charts: Dict[str, str], request: ReportRequest) -> str:
        """Generate HTML report"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{ report_title }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .header { background: #2c3e50; color: white; padding: 20px; margin-bottom: 30px; }
                .section { margin-bottom: 30px; }
                .chart { text-align: center; margin: 20px 0; }
                .chart img { max-width: 100%; }
                .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                .table th, .table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                .table th { background-color: #f2f2f2; }
                .critical { color: #e74c3c; font-weight: bold; }
                .high { color: #f39c12; font-weight: bold; }
                .medium { color: #f1c40f; font-weight: bold; }
                .low { color: #27ae60; font-weight: bold; }
                .summary-box { background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{{ report_title }}</h1>
                <p>Generated on {{ generated_at }}</p>
                <p>Period: {{ date_range.start }} to {{ date_range.end }}</p>
            </div>
            
            {% if data.violation_counts %}
            <div class="section">
                <h2>Violation Summary</h2>
                <div class="summary-box">
                    <p><strong>Total Violations:</strong> {{ data.violation_counts.total_violations }}</p>
                    <p><span class="critical">Critical:</span> {{ data.violation_counts.critical or 0 }}</p>
                    <p><span class="high">High:</span> {{ data.violation_counts.high or 0 }}</p>
                    <p><span class="medium">Medium:</span> {{ data.violation_counts.medium or 0 }}</p>
                    <p><span class="low">Low:</span> {{ data.violation_counts.low or 0 }}</p>
                </div>
            </div>
            {% endif %}
            
            {% if charts.severity_distribution %}
            <div class="section">
                <h2>Violations by Severity</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{{ charts.severity_distribution }}" alt="Severity Distribution">
                </div>
            </div>
            {% endif %}
            
            {% if data.top_violated_rules %}
            <div class="section">
                <h2>Most Violated Rules</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Rule ID</th>
                            <th>Violations</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for rule in data.top_violated_rules %}
                        <tr>
                            <td>{{ rule.rule_id }}</td>
                            <td>{{ rule.count }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            {% if data.critical_violations %}
            <div class="section">
                <h2>Critical Violations</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Violation ID</th>
                            <th>Rule</th>
                            <th>User</th>
                            <th>Service</th>
                            <th>Description</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for violation in data.critical_violations %}
                        <tr>
                            <td>{{ violation.violation_id }}</td>
                            <td>{{ violation.rule_id }}</td>
                            <td>{{ violation.user_id or 'N/A' }}</td>
                            <td>{{ violation.service_name or 'N/A' }}</td>
                            <td>{{ violation.description }}</td>
                            <td>{{ violation.status }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}
            
            {% for chart_name, chart_data in charts.items() %}
            {% if chart_name != 'severity_distribution' %}
            <div class="section">
                <h2>{{ chart_name.replace('_', ' ').title() }}</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{{ chart_data }}" alt="{{ chart_name }}">
                </div>
            </div>
            {% endif %}
            {% endfor %}
            
        </body>
        </html>
        """
        
        template = Template(html_template)
        
        report_title = f"{request.report_type.value.replace('_', ' ').title()} Report"
        
        return template.render(
            report_title=report_title,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            date_range={
                "start": request.start_date.strftime("%Y-%m-%d"),
                "end": request.end_date.strftime("%Y-%m-%d")
            },
            data=data,
            charts=charts
        )
    
    async def _generate_csv_report(self, data: Dict[str, Any], request: ReportRequest) -> str:
        """Generate CSV report"""
        # This is a simplified CSV generation - would need more specific logic per report type
        csv_lines = []
        
        if request.report_type == ReportType.VIOLATION_ANALYSIS and data.get("violation_patterns"):
            csv_lines.append("Rule ID,Frequency,Avg Duration (min),Affected Users")
            for pattern in data["violation_patterns"]:
                csv_lines.append(f"{pattern['rule_id']},{pattern['frequency']},{pattern.get('avg_duration_minutes', 0):.1f},{pattern['affected_users']}")
        
        return "\n".join(csv_lines)
    
    async def schedule_report(self, request: ReportRequest, schedule: str, recipients: List[str]) -> str:
        """Schedule a recurring report (placeholder for future implementation)"""
        # This would integrate with a job scheduler like Celery or APScheduler
        logger.info(f"Scheduled {request.report_type.value} report for {schedule} to {recipients}")
        return f"report_schedule_{int(datetime.now().timestamp())}"

if __name__ == "__main__":
    # Test the reporter
    async def test_reporter():
        reporter = ComplianceReporter()
        
        request = ReportRequest(
            report_type=ReportType.DAILY_SUMMARY,
            format=ReportFormat.HTML,
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now()
        )
        
        try:
            report = await reporter.generate_report(request)
            print("Report generated successfully")
            print(f"Report ID: {report['report_id']}")
            
            # Save HTML report to file for testing
            with open("/tmp/compliance_report.html", "w") as f:
                f.write(report['formatted_output'])
            print("Report saved to /tmp/compliance_report.html")
            
        except Exception as e:
            print(f"Error generating report: {e}")
    
    asyncio.run(test_reporter())