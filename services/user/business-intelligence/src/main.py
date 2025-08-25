#!/usr/bin/env python3
"""
Healthcare Business Intelligence Service

Provides analytics, reporting, and business insights for the Intelluxe AI healthcare system.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import asyncpg
import httpx
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import redis.asyncio as redis

from models.bi_models import (
    ReportRequest,
    ReportType,
    BusinessReport,
    Dashboard,
    Metric,
    MetricType,
    Visualization,
    ChartType,
    FinancialSummary,
    OperationalMetrics,
    PatientAnalytics,
    QualityMetrics,
    TrendAnalysis,
    Alert,
    AlertRule,
    TimePeriod,
)


class BusinessIntelligenceService:
    def __init__(self):
        self.app = FastAPI(
            title="Healthcare Business Intelligence",
            description="Analytics and reporting service for healthcare operations",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.alert_rules: Dict[str, AlertRule] = {}
        self.setup_routes()
        self.setup_middleware()
        
    def setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            try:
                if self.db_pool:
                    async with self.db_pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")
                
                if self.redis_client:
                    await self.redis_client.ping()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.utcnow(),
                    "service": "business-intelligence",
                    "version": "1.0.0"
                }
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return {"status": "unhealthy", "error": str(e)}

        @self.app.post("/reports/generate", response_model=BusinessReport)
        async def generate_report(
            request: ReportRequest,
            background_tasks: BackgroundTasks
        ):
            """Generate a business intelligence report"""
            try:
                report = await self.create_business_report(request)
                
                # Cache the report for future access
                background_tasks.add_task(self.cache_report, report)
                
                return report
            except Exception as e:
                logger.error(f"Failed to generate report: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/reports/{report_id}", response_model=BusinessReport)
        async def get_report(report_id: str):
            """Retrieve a previously generated report"""
            try:
                report = await self.get_cached_report(report_id)
                if not report:
                    raise HTTPException(status_code=404, detail="Report not found")
                return report
            except Exception as e:
                logger.error(f"Failed to retrieve report: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/dashboard", response_model=Dashboard)
        async def get_dashboard(dashboard_name: str = Query("main")):
            """Get real-time business intelligence dashboard"""
            try:
                return await self.create_dashboard(dashboard_name)
            except Exception as e:
                logger.error(f"Failed to get dashboard: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/metrics/financial", response_model=FinancialSummary)
        async def get_financial_metrics(
            start_date: datetime = Query(...),
            end_date: datetime = Query(...)
        ):
            """Get financial performance metrics"""
            try:
                return await self.calculate_financial_metrics(start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to get financial metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/metrics/operational", response_model=OperationalMetrics)
        async def get_operational_metrics(
            start_date: datetime = Query(...),
            end_date: datetime = Query(...)
        ):
            """Get operational performance metrics"""
            try:
                return await self.calculate_operational_metrics(start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to get operational metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/analytics/patients", response_model=PatientAnalytics)
        async def get_patient_analytics(
            start_date: datetime = Query(...),
            end_date: datetime = Query(...)
        ):
            """Get patient-focused analytics"""
            try:
                return await self.analyze_patient_data(start_date, end_date)
            except Exception as e:
                logger.error(f"Failed to get patient analytics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/analytics/trends", response_model=List[TrendAnalysis])
        async def get_trend_analysis(
            metrics: List[str] = Query(...),
            period_days: int = Query(90, ge=7, le=365)
        ):
            """Get trend analysis for specified metrics"""
            try:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=period_days)
                
                analyses = []
                for metric in metrics:
                    analysis = await self.perform_trend_analysis(metric, start_date, end_date)
                    if analysis:
                        analyses.append(analysis)
                
                return analyses
            except Exception as e:
                logger.error(f"Failed to perform trend analysis: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/alerts", response_model=List[Alert])
        async def get_alerts(
            active_only: bool = Query(True),
            severity: Optional[str] = Query(None)
        ):
            """Get business intelligence alerts"""
            try:
                return await self.get_active_alerts(active_only, severity)
            except Exception as e:
                logger.error(f"Failed to get alerts: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/alerts/rules")
        async def add_alert_rule(rule: AlertRule):
            """Add a new alert rule"""
            try:
                await self.create_alert_rule(rule)
                return {
                    "rule_id": rule.rule_id,
                    "status": "created",
                    "enabled": rule.enabled
                }
            except Exception as e:
                logger.error(f"Failed to create alert rule: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/visualizations/chart")
        async def create_chart(
            chart_type: ChartType = Query(...),
            metric: str = Query(...),
            start_date: datetime = Query(...),
            end_date: datetime = Query(...)
        ):
            """Create a data visualization chart"""
            try:
                chart = await self.generate_chart(chart_type, metric, start_date, end_date)
                return chart
            except Exception as e:
                logger.error(f"Failed to create chart: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def startup(self):
        """Initialize service connections and background tasks"""
        try:
            # Initialize database connection
            postgres_url = os.getenv('POSTGRES_URL')
            if not postgres_url:
                raise ValueError("POSTGRES_URL environment variable not set")
            
            self.db_pool = await asyncpg.create_pool(postgres_url, min_size=5, max_size=20)
            await self.create_tables()
            
            # Initialize Redis connection
            redis_url = os.getenv('REDIS_URL', 'redis://172.20.0.12:6379')
            self.redis_client = redis.from_url(redis_url)
            
            # Initialize HTTP client for service communication
            self.http_client = httpx.AsyncClient(timeout=30.0)
            
            # Load alert rules
            await self.load_alert_rules()
            
            # Start background monitoring task
            asyncio.create_task(self.monitor_metrics())
            
            logger.info("Business Intelligence service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Business Intelligence service: {e}")
            raise

    async def shutdown(self):
        """Clean up resources"""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.http_client:
            await self.http_client.aclose()

    async def create_tables(self):
        """Create database tables for BI service"""
        async with self.db_pool.acquire() as conn:
            # Reports table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bi_reports (
                    report_id VARCHAR PRIMARY KEY,
                    report_type VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    period_start TIMESTAMP WITH TIME ZONE,
                    period_end TIMESTAMP WITH TIME ZONE,
                    data JSONB NOT NULL,
                    requested_by VARCHAR,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # Metrics table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bi_metrics (
                    metric_id VARCHAR PRIMARY KEY,
                    metric_name VARCHAR NOT NULL,
                    metric_type VARCHAR NOT NULL,
                    value NUMERIC NOT NULL,
                    unit VARCHAR,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    source VARCHAR NOT NULL,
                    metadata JSONB DEFAULT '{}'
                )
            ''')
            
            # Alert rules table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bi_alert_rules (
                    rule_id VARCHAR PRIMARY KEY,
                    rule_name VARCHAR NOT NULL,
                    metric_name VARCHAR NOT NULL,
                    condition VARCHAR NOT NULL,
                    threshold_value NUMERIC NOT NULL,
                    severity VARCHAR NOT NULL,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_triggered TIMESTAMP WITH TIME ZONE
                )
            ''')
            
            # Alerts table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS bi_alerts (
                    alert_id VARCHAR PRIMARY KEY,
                    rule_id VARCHAR REFERENCES bi_alert_rules(rule_id),
                    metric_name VARCHAR NOT NULL,
                    current_value NUMERIC NOT NULL,
                    threshold_value NUMERIC NOT NULL,
                    severity VARCHAR NOT NULL,
                    message TEXT NOT NULL,
                    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    acknowledged BOOLEAN DEFAULT FALSE,
                    resolved BOOLEAN DEFAULT FALSE
                )
            ''')

    async def create_business_report(self, request: ReportRequest) -> BusinessReport:
        """Create a comprehensive business report"""
        report_id = str(uuid.uuid4())
        
        # Generate report based on type
        if request.report_type == ReportType.FINANCIAL_SUMMARY:
            report_data = await self.generate_financial_report(request)
        elif request.report_type == ReportType.OPERATIONAL_METRICS:
            report_data = await self.generate_operational_report(request)
        elif request.report_type == ReportType.PATIENT_ANALYTICS:
            report_data = await self.generate_patient_report(request)
        else:
            report_data = await self.generate_general_report(request)
        
        report = BusinessReport(
            report_id=report_id,
            report_type=request.report_type,
            title=f"{request.report_type.value.replace('_', ' ').title()} Report",
            period_start=request.start_date,
            period_end=request.end_date,
            requested_by=request.requested_by,
            **report_data
        )
        
        # Store report in database
        await self.store_report(report)
        
        return report

    async def generate_financial_report(self, request: ReportRequest) -> Dict[str, Any]:
        """Generate financial performance report"""
        financial_metrics = await self.calculate_financial_metrics(
            request.start_date, request.end_date
        )
        
        # Create visualizations
        visualizations = []
        if request.include_visualizations:
            # Revenue trend chart
            revenue_chart = await self.generate_chart(
                ChartType.LINE, "revenue", request.start_date, request.end_date
            )
            visualizations.append(revenue_chart)
            
            # Cost breakdown pie chart
            cost_chart = await self.create_cost_breakdown_chart(financial_metrics)
            visualizations.append(cost_chart)
        
        return {
            "key_metrics": self._financial_to_metrics(financial_metrics),
            "visualizations": visualizations,
            "detailed_data": {"financial_summary": financial_metrics.model_dump()},
            "insights": await self.generate_financial_insights(financial_metrics),
            "recommendations": await self.generate_financial_recommendations(financial_metrics)
        }

    async def generate_operational_report(self, request: ReportRequest) -> Dict[str, Any]:
        """Generate operational metrics report"""
        op_metrics = await self.calculate_operational_metrics(
            request.start_date, request.end_date
        )
        
        visualizations = []
        if request.include_visualizations:
            # Patient volume chart
            volume_chart = await self.generate_chart(
                ChartType.BAR, "patient_volume", request.start_date, request.end_date
            )
            visualizations.append(volume_chart)
        
        return {
            "key_metrics": self._operational_to_metrics(op_metrics),
            "visualizations": visualizations,
            "detailed_data": {"operational_metrics": op_metrics.model_dump()},
            "insights": await self.generate_operational_insights(op_metrics),
            "recommendations": await self.generate_operational_recommendations(op_metrics)
        }

    async def generate_patient_report(self, request: ReportRequest) -> Dict[str, Any]:
        """Generate patient analytics report"""
        patient_analytics = await self.analyze_patient_data(
            request.start_date, request.end_date
        )
        
        return {
            "key_metrics": self._patient_to_metrics(patient_analytics),
            "visualizations": [],
            "detailed_data": {"patient_analytics": patient_analytics.model_dump()},
            "insights": await self.generate_patient_insights(patient_analytics),
            "recommendations": []
        }

    async def generate_general_report(self, request: ReportRequest) -> Dict[str, Any]:
        """Generate a general business report"""
        return {
            "key_metrics": [],
            "visualizations": [],
            "detailed_data": {},
            "insights": ["Report generated successfully"],
            "recommendations": []
        }

    async def calculate_financial_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> FinancialSummary:
        """Calculate financial performance metrics"""
        try:
            # Get billing data from billing-engine service
            billing_url = os.getenv('BILLING_ENGINE_URL', 'http://172.20.0.24:8004')
            
            async with self.http_client.get(
                f"{billing_url}/analytics/revenue",
                params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
            ) as response:
                if response.status_code == 200:
                    billing_data = response.json()
                else:
                    billing_data = {"total_revenue": 0, "total_costs": 0}
                    
        except Exception as e:
            logger.warning(f"Failed to fetch billing data: {e}")
            billing_data = {"total_revenue": 0, "total_costs": 0}
        
        total_revenue = billing_data.get("total_revenue", 0)
        total_costs = billing_data.get("total_costs", 0)
        net_income = total_revenue - total_costs
        gross_margin = (net_income / total_revenue * 100) if total_revenue > 0 else 0
        
        return FinancialSummary(
            total_revenue=total_revenue,
            total_costs=total_costs,
            net_income=net_income,
            gross_margin=gross_margin,
            operating_margin=gross_margin,  # Simplified
            revenue_by_service=billing_data.get("revenue_by_service", {}),
            cost_by_category=billing_data.get("cost_by_category", {})
        )

    async def calculate_operational_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> OperationalMetrics:
        """Calculate operational performance metrics"""
        # Query healthcare-api for operational data
        try:
            healthcare_url = os.getenv('HEALTHCARE_API_URL', 'http://172.20.0.11:8000')
            
            # For now, return mock data - would integrate with real services
            return OperationalMetrics(
                patient_volume=150,
                appointment_utilization=85.5,
                no_show_rate=12.3,
                average_wait_time=18.5,
                staff_productivity={"doctors": 90.2, "nurses": 88.7},
                resource_utilization={"rooms": 78.4, "equipment": 82.1},
                service_volumes={"consultations": 120, "procedures": 30},
                capacity_metrics={"overall": 83.2}
            )
            
        except Exception as e:
            logger.error(f"Failed to calculate operational metrics: {e}")
            raise

    async def analyze_patient_data(
        self, start_date: datetime, end_date: datetime
    ) -> PatientAnalytics:
        """Analyze patient data and demographics"""
        # Mock patient analytics - would integrate with real patient data
        return PatientAnalytics(
            total_patients=1250,
            new_patients=85,
            patient_demographics={
                "age_groups": {"0-18": 15, "19-35": 25, "36-65": 45, "65+": 15},
                "gender": {"male": 48, "female": 52}
            },
            visit_frequency={"1": 30, "2-5": 45, "6+": 25},
            patient_satisfaction=4.2,
            retention_rate=87.3
        )

    async def generate_chart(
        self, chart_type: ChartType, metric: str, start_date: datetime, end_date: datetime
    ) -> Visualization:
        """Generate a data visualization chart"""
        chart_id = str(uuid.uuid4())
        
        # Mock data for demonstration
        if chart_type == ChartType.LINE:
            # Generate sample time series data
            dates = pd.date_range(start_date, end_date, freq='D')
            values = [100 + i * 2 + (i % 7) * 10 for i in range(len(dates))]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=values,
                mode='lines+markers',
                name=metric
            ))
            fig.update_layout(title=f"{metric} Trend", xaxis_title="Date", yaxis_title="Value")
            
            chart_data = fig.to_dict()
            
        elif chart_type == ChartType.BAR:
            categories = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
            values = [45, 52, 38, 61, 48]
            
            fig = go.Figure(data=[go.Bar(x=categories, y=values)])
            fig.update_layout(title=f"{metric} by Day")
            
            chart_data = fig.to_dict()
            
        else:
            chart_data = {"type": chart_type.value, "data": []}
        
        return Visualization(
            chart_id=chart_id,
            title=f"{metric} {chart_type.value.title()} Chart",
            chart_type=chart_type,
            data=chart_data
        )

    async def create_cost_breakdown_chart(self, financial: FinancialSummary) -> Visualization:
        """Create cost breakdown pie chart"""
        if not financial.cost_by_category:
            cost_data = {"Staff": 60, "Equipment": 20, "Supplies": 15, "Other": 5}
        else:
            cost_data = financial.cost_by_category
            
        fig = go.Figure(data=[go.Pie(
            labels=list(cost_data.keys()),
            values=list(cost_data.values())
        )])
        fig.update_layout(title="Cost Breakdown")
        
        return Visualization(
            chart_id=str(uuid.uuid4()),
            title="Cost Breakdown",
            chart_type=ChartType.PIE,
            data=fig.to_dict()
        )

    def _financial_to_metrics(self, financial: FinancialSummary) -> List[Metric]:
        """Convert financial summary to metrics list"""
        return [
            Metric(
                metric_id="revenue",
                metric_name="Total Revenue",
                metric_type=MetricType.REVENUE,
                value=financial.total_revenue,
                unit="USD",
                source="billing-engine"
            ),
            Metric(
                metric_id="costs",
                metric_name="Total Costs",
                metric_type=MetricType.COST,
                value=financial.total_costs,
                unit="USD",
                source="billing-engine"
            ),
            Metric(
                metric_id="margin",
                metric_name="Gross Margin",
                metric_type=MetricType.EFFICIENCY,
                value=financial.gross_margin,
                unit="%",
                source="calculated"
            )
        ]

    def _operational_to_metrics(self, operational: OperationalMetrics) -> List[Metric]:
        """Convert operational metrics to metrics list"""
        return [
            Metric(
                metric_id="volume",
                metric_name="Patient Volume",
                metric_type=MetricType.VOLUME,
                value=operational.patient_volume,
                unit="patients",
                source="healthcare-api"
            ),
            Metric(
                metric_id="utilization",
                metric_name="Appointment Utilization",
                metric_type=MetricType.EFFICIENCY,
                value=operational.appointment_utilization,
                unit="%",
                source="healthcare-api"
            )
        ]

    def _patient_to_metrics(self, patient: PatientAnalytics) -> List[Metric]:
        """Convert patient analytics to metrics list"""
        return [
            Metric(
                metric_id="total_patients",
                metric_name="Total Patients",
                metric_type=MetricType.VOLUME,
                value=patient.total_patients,
                unit="patients",
                source="healthcare-api"
            ),
            Metric(
                metric_id="satisfaction",
                metric_name="Patient Satisfaction",
                metric_type=MetricType.SATISFACTION,
                value=patient.patient_satisfaction,
                unit="score",
                source="surveys"
            )
        ]

    async def generate_financial_insights(self, financial: FinancialSummary) -> List[str]:
        """Generate insights from financial data"""
        insights = []
        
        if financial.gross_margin > 20:
            insights.append("Strong gross margin indicates healthy financial performance")
        elif financial.gross_margin < 10:
            insights.append("Low gross margin suggests need for cost optimization")
            
        if financial.total_revenue > 0:
            insights.append(f"Revenue of ${financial.total_revenue:,.2f} for the period")
            
        return insights

    async def generate_financial_recommendations(self, financial: FinancialSummary) -> List[str]:
        """Generate recommendations from financial data"""
        recommendations = []
        
        if financial.gross_margin < 15:
            recommendations.append("Consider cost reduction initiatives")
            recommendations.append("Review pricing strategy for services")
            
        return recommendations

    async def generate_operational_insights(self, operational: OperationalMetrics) -> List[str]:
        """Generate insights from operational data"""
        insights = []
        
        if operational.no_show_rate > 15:
            insights.append("High no-show rate impacting capacity utilization")
            
        if operational.appointment_utilization > 90:
            insights.append("Near maximum appointment capacity utilization")
            
        return insights

    async def generate_operational_recommendations(self, operational: OperationalMetrics) -> List[str]:
        """Generate recommendations from operational data"""
        recommendations = []
        
        if operational.no_show_rate > 15:
            recommendations.append("Implement reminder system to reduce no-shows")
            
        return recommendations

    async def generate_patient_insights(self, patient: PatientAnalytics) -> List[str]:
        """Generate insights from patient data"""
        insights = []
        
        if patient.patient_satisfaction >= 4.0:
            insights.append("High patient satisfaction scores")
        elif patient.patient_satisfaction < 3.5:
            insights.append("Patient satisfaction below target levels")
            
        return insights

    async def perform_trend_analysis(
        self, metric: str, start_date: datetime, end_date: datetime
    ) -> Optional[TrendAnalysis]:
        """Perform trend analysis on a metric"""
        try:
            # Mock trend data - would analyze real metrics
            days = (end_date - start_date).days
            time_series = []
            
            for i in range(days):
                date = start_date + timedelta(days=i)
                value = 100 + i * 0.5 + (i % 7) * 5
                time_series.append({
                    "date": date.isoformat(),
                    "value": value
                })
            
            # Simple trend calculation
            first_val = time_series[0]["value"] if time_series else 0
            last_val = time_series[-1]["value"] if time_series else 0
            growth_rate = ((last_val - first_val) / first_val * 100) if first_val > 0 else 0
            
            if growth_rate > 5:
                trend_direction = "up"
            elif growth_rate < -5:
                trend_direction = "down"
            else:
                trend_direction = "stable"
            
            return TrendAnalysis(
                metric_name=metric,
                time_series_data=time_series,
                trend_direction=trend_direction,
                growth_rate=growth_rate,
                seasonal_patterns=[],
                anomalies=[],
                forecast=[]
            )
            
        except Exception as e:
            logger.error(f"Failed to perform trend analysis for {metric}: {e}")
            return None

    async def create_dashboard(self, dashboard_name: str) -> Dashboard:
        """Create real-time dashboard"""
        # Get current metrics
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        financial = await self.calculate_financial_metrics(start_date, end_date)
        operational = await self.calculate_operational_metrics(start_date, end_date)
        
        metrics = []
        metrics.extend(self._financial_to_metrics(financial))
        metrics.extend(self._operational_to_metrics(operational))
        
        # Get active alerts
        alerts = await self.get_active_alerts(True, None)
        
        return Dashboard(
            dashboard_id=str(uuid.uuid4()),
            dashboard_name=dashboard_name,
            metrics=metrics,
            visualizations=[],
            alerts=[alert.model_dump() for alert in alerts[:5]]
        )

    async def get_active_alerts(self, active_only: bool, severity: Optional[str]) -> List[Alert]:
        """Get current alerts"""
        query = "SELECT * FROM bi_alerts WHERE 1=1"
        params = []
        param_count = 0
        
        if active_only:
            query += " AND resolved = FALSE"
            
        if severity:
            param_count += 1
            query += f" AND severity = ${param_count}"
            params.append(severity)
            
        query += " ORDER BY triggered_at DESC LIMIT 50"
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [Alert(**dict(row)) for row in rows]

    async def load_alert_rules(self):
        """Load alert rules from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rules = await conn.fetch("SELECT * FROM bi_alert_rules WHERE enabled = TRUE")
                
                for row in rules:
                    rule = AlertRule(**dict(row))
                    self.alert_rules[rule.rule_id] = rule
                    
            logger.info(f"Loaded {len(self.alert_rules)} alert rules")
        except Exception as e:
            logger.error(f"Failed to load alert rules: {e}")

    async def create_alert_rule(self, rule: AlertRule):
        """Create a new alert rule"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO bi_alert_rules (
                    rule_id, rule_name, metric_name, condition,
                    threshold_value, severity, enabled
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''',
                rule.rule_id, rule.rule_name, rule.metric_name,
                rule.condition, rule.threshold_value, rule.severity,
                rule.enabled
            )
            
        self.alert_rules[rule.rule_id] = rule

    async def monitor_metrics(self):
        """Background task to monitor metrics and trigger alerts"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                # Check each alert rule
                for rule in self.alert_rules.values():
                    if rule.enabled:
                        await self.check_alert_rule(rule)
                        
            except Exception as e:
                logger.error(f"Error in metric monitoring: {e}")
                await asyncio.sleep(60)

    async def check_alert_rule(self, rule: AlertRule):
        """Check if an alert rule should trigger"""
        try:
            # Get current metric value
            current_value = await self.get_current_metric_value(rule.metric_name)
            
            if current_value is None:
                return
                
            # Check condition
            triggered = False
            if rule.condition == ">" and current_value > rule.threshold_value:
                triggered = True
            elif rule.condition == "<" and current_value < rule.threshold_value:
                triggered = True
            elif rule.condition == "=" and current_value == rule.threshold_value:
                triggered = True
                
            if triggered:
                await self.create_alert(rule, current_value)
                
        except Exception as e:
            logger.error(f"Error checking alert rule {rule.rule_id}: {e}")

    async def get_current_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for a metric"""
        try:
            # Mock implementation - would get real metric values
            metric_values = {
                "revenue": 50000.0,
                "costs": 35000.0,
                "patient_volume": 150.0,
                "satisfaction": 4.2
            }
            return metric_values.get(metric_name)
        except Exception as e:
            logger.error(f"Failed to get metric value for {metric_name}: {e}")
            return None

    async def create_alert(self, rule: AlertRule, current_value: float):
        """Create a new alert"""
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            rule_id=rule.rule_id,
            metric_name=rule.metric_name,
            current_value=current_value,
            threshold_value=rule.threshold_value,
            severity=rule.severity,
            message=f"{rule.metric_name} is {current_value} (threshold: {rule.threshold_value})"
        )
        
        # Store in database
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO bi_alerts (
                    alert_id, rule_id, metric_name, current_value,
                    threshold_value, severity, message
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''',
                alert.alert_id, alert.rule_id, alert.metric_name,
                alert.current_value, alert.threshold_value,
                alert.severity, alert.message
            )
            
        # Update rule trigger time
        await conn.execute('''
            UPDATE bi_alert_rules 
            SET last_triggered = NOW() 
            WHERE rule_id = $1
        ''', rule.rule_id)

    async def store_report(self, report: BusinessReport):
        """Store report in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO bi_reports (
                    report_id, report_type, title, period_start,
                    period_end, data, requested_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            ''',
                report.report_id, report.report_type.value, report.title,
                report.period_start, report.period_end,
                report.model_dump_json(), report.requested_by
            )

    async def cache_report(self, report: BusinessReport):
        """Cache report in Redis"""
        await self.redis_client.setex(
            f"report:{report.report_id}",
            3600,  # 1 hour expiry
            report.model_dump_json()
        )

    async def get_cached_report(self, report_id: str) -> Optional[BusinessReport]:
        """Get cached report from Redis"""
        try:
            cached = await self.redis_client.get(f"report:{report_id}")
            if cached:
                return BusinessReport.model_validate_json(cached)
                
            # If not in cache, try database
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM bi_reports WHERE report_id = $1", report_id
                )
                if row:
                    report_data = json.loads(row['data'])
                    return BusinessReport(**report_data)
                    
        except Exception as e:
            logger.error(f"Failed to get cached report: {e}")
            
        return None


# Application instance
bi_service = BusinessIntelligenceService()
app = bi_service.app


@app.on_event("startup")
async def startup_event():
    await bi_service.startup()


@app.on_event("shutdown")
async def shutdown_event():
    await bi_service.shutdown()


def main():
    """Main entry point"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(
        "/app/logs/business-intelligence.log",
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )
    logger.add(
        lambda msg: print(msg, end=""),
        level=log_level,
        format="{time:HH:mm:ss} | {level: <8} | {message}"
    )
    
    logger.info("Starting Healthcare Business Intelligence Service...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8006,
        log_level=log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()