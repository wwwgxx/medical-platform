# -*- coding: utf-8 -*-
"""
医疗运营数据决策平台 - Flask Backend with MySQL
"""
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pymysql
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ========== 数据库连接 ==========
def get_db():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='hospital_ops',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def query_db(sql, params=None):
    """执行SQL查询，返回字典列表"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()

def query_one(sql, params=None):
    """执行SQL查询，返回单行"""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    finally:
        conn.close()

# ========== 菜单配置（基于数据库结构） ==========
TOP_NAV = {
    "门诊管理": {
        "icon": "fa-stethoscope",
        "color": "#3b82f6",
        "reports": {
            "门诊挂号统计": {"id": "opd_reg", "icon": "fa-calendar-check", "desc": "按科室/医生/日期统计挂号量、挂号类型分布"},
            "门诊诊断分析": {"id": "opd_diag", "icon": "fa-stethoscope", "desc": "常见病种统计、主诊断分布"},
            "门诊收费汇总": {"id": "opd_bill", "icon": "fa-yen-sign", "desc": "门诊收入、支付方式分析、医保自付比例"},
        }
    },
    "住院管理": {
        "icon": "fa-bed",
        "color": "#8b5cf6",
        "reports": {
            "入院登记统计": {"id": "inp_admit", "icon": "fa-sign-in-alt", "desc": "入院人数、病情分布、入院途径"},
            "出院患者分析": {"id": "inp_discharge", "icon": "fa-sign-out-alt", "desc": "出院情况、住院天数、费用分析"},
            "床位使用监控": {"id": "inp_bed", "icon": "fa-bed", "desc": "床位占用率、病区容量、床位周转"},
            "住院费用明细": {"id": "inp_bill", "icon": "fa-file-invoice-dollar", "desc": "费用类型分布、医保/自付比例"},
        }
    },
    "药品管理": {
        "icon": "fa-pills",
        "color": "#10b981",
        "reports": {
            "药品库存查询": {"id": "drug_stock", "icon": "fa-boxes", "desc": "库存状态、效期预警、库存成本"},
            "处方用药分析": {"id": "drug_rx", "icon": "fa-prescription", "desc": "处方统计、用药频次、药品消耗"},
            "耗材管理": {"id": "drug_cons", "icon": "fa-syringe", "desc": "耗材库存、供应商、采购分析"},
        }
    },
    "手术管理": {
        "icon": "fa-procedures",
        "color": "#06b6d4",
        "reports": {
            "手术记录统计": {"id": "surg_record", "icon": "fa-syringe", "desc": "手术量、等级分布、成功率"},
            "检查检验分析": {"id": "exam_stat", "icon": "fa-microscope", "desc": "检查类型、异常率、费用"},
            "设备使用统计": {"id": "equip_stat", "icon": "fa-x-ray", "desc": "设备使用时长、故障率、科室分布"},
        }
    },
    "财务分析": {
        "icon": "fa-chart-bar",
        "color": "#f59e0b",
        "reports": {
            "每日运营统计": {"id": "fin_daily", "icon": "fa-calendar-day", "desc": "门诊量/收入、住院日/收入、净利润趋势"},
            "科室绩效排名": {"id": "fin_perf", "icon": "fa-trophy", "desc": "绩效评分、等级、收入目标达成率"},
            "医保结算分析": {"id": "fin_ins", "icon": "fa-hand-holding-medical", "desc": "结算金额、报销比例、结算状态"},
        }
    },
    "质量监控": {
        "icon": "fa-shield-alt",
        "color": "#ef4444",
        "reports": {
            "质量指标监控": {"id": "qual_metric", "icon": "fa-chart-line", "desc": "各项指标达标情况、预警状态"},
            "患者满意度": {"id": "qual_sat", "icon": "fa-smile", "desc": "满意度趋势、科室对比"},
        }
    }
}

# 报表SQL配置
REPORT_SQL = {
    # ===== 门诊管理 =====
    "opd_reg": {
        "title": "门诊挂号统计",
        "sql": """
            SELECT r.reg_date, d.dept_name AS 科室, s.name AS 医生, r.reg_type AS 挂号类型,
                   COUNT(*) AS 挂号数, SUM(r.reg_fee) AS 挂号费合计
            FROM outpatient_registrations r
            JOIN departments d ON r.department_id = d.id
            JOIN staff s ON r.doctor_id = s.id
            GROUP BY r.reg_date, d.dept_name, s.name, r.reg_type
            ORDER BY r.reg_date DESC, d.dept_name
        """,
        "charts": [
            {"type": "pie", "title": "挂号类型分布", "label": "挂号类型", "value": "挂号数"},
            {"type": "bar", "title": "科室挂号量", "x": "科室", "y": "挂号数"},
            {"type": "line", "title": "挂号趋势", "x": "reg_date", "y": "挂号数"},
        ]
    },
    "opd_diag": {
        "title": "门诊诊断分析",
        "sql": """
            SELECT od.diagnosis_name AS 诊断, od.diagnosis_type AS 类型,
                   COUNT(*) AS 人数
            FROM outpatient_diagnoses od
            GROUP BY od.diagnosis_name, od.diagnosis_type
            ORDER BY 人数 DESC
        """,
        "charts": [
            {"type": "pie", "title": "疾病分布", "label": "诊断", "value": "人数"},
            {"type": "bar", "title": "诊断人数TOP", "x": "诊断", "y": "人数"},
        ]
    },
    "opd_bill": {
        "title": "门诊收费汇总",
        "sql": """
            SELECT ob.pay_method AS 支付方式, COUNT(*) AS 笔数,
                   SUM(ob.total_amount) AS 总金额,
                   SUM(ob.insurance_pay) AS 医保支付,
                   SUM(ob.self_pay) AS 自付金额,
                   ROUND(SUM(ob.total_amount)/SUM(SUM(ob.total_amount)) OVER()*100, 2) AS 金额占比
            FROM outpatient_billing ob
            WHERE ob.status = '已收费'
            GROUP BY ob.pay_method
            ORDER BY 总金额 DESC
        """,
        "charts": [
            {"type": "pie", "title": "支付方式分布", "label": "支付方式", "value": "总金额"},
            {"type": "bar", "title": "各支付方式金额", "x": "支付方式", "y": "总金额"},
        ]
    },

    # ===== 住院管理 =====
    "inp_admit": {
        "title": "入院登记统计",
        "sql": """
            SELECT d.dept_name AS 科室, ia.admission_source AS 入院途径,
                   ia.patient_condition AS 病情, COUNT(*) AS 人数,
                   SUM(ia.deposit_amount) AS 押金合计
            FROM inpatient_admissions ia
            JOIN departments d ON ia.department_id = d.id
            GROUP BY d.dept_name, ia.admission_source, ia.patient_condition
            ORDER BY 人数 DESC
        """,
        "charts": [
            {"type": "pie", "title": "入院途径分布", "label": "入院途径", "value": "人数"},
            {"type": "bar", "title": "科室入院人数", "x": "科室", "y": "人数"},
        ]
    },
    "inp_discharge": {
        "title": "出院患者分析",
        "sql": """
            SELECT d.dept_name AS 科室, di.discharge_condition AS 出院情况,
                   COUNT(*) AS 人数,
                   ROUND(AVG(di.los_days), 1) AS 平均住院天数,
                   ROUND(AVG(di.total_cost), 2) AS 平均费用,
                   SUM(di.insurance_pay_amount) AS 医保支付总额
            FROM discharges di
            JOIN inpatient_admissions ia ON di.admission_id = ia.id
            JOIN departments d ON ia.department_id = d.id
            GROUP BY d.dept_name, di.discharge_condition
            ORDER BY 人数 DESC
        """,
        "charts": [
            {"type": "pie", "title": "出院情况分布", "label": "出院情况", "value": "人数"},
            {"type": "bar", "title": "科室出院人数", "x": "科室", "y": "人数"},
        ]
    },
    "inp_bed": {
        "title": "床位使用监控",
        "sql": """
            SELECT w.ward_name AS 病区, w.ward_type AS 病区类型,
                   w.bed_count AS 床位数,
                   SUM(CASE WHEN b.status = '占用' THEN 1 ELSE 0 END) AS 已占用,
                   SUM(CASE WHEN b.status = '空闲' THEN 1 ELSE 0 END) AS 空闲,
                   ROUND(SUM(CASE WHEN b.status = '占用' THEN 1 ELSE 0 END) / w.bed_count * 100, 1) AS 使用率
            FROM wards w
            JOIN beds b ON b.ward_id = w.id
            GROUP BY w.ward_name, w.ward_type, w.bed_count
            ORDER BY 使用率 DESC
        """,
        "charts": [
            {"type": "bar", "title": "病区床位使用率", "x": "病区", "y": "使用率"},
            {"type": "pie", "title": "病区类型分布", "label": "病区类型", "value": "床位数"},
        ]
    },
    "inp_bill": {
        "title": "住院费用明细",
        "sql": """
            SELECT ib.item_type AS 费用类型, COUNT(*) AS 笔数,
                   SUM(ib.amount) AS 总金额,
                   ROUND(AVG(ib.amount), 2) AS 平均金额,
                   SUM(ib.insurance_pay) AS 医保支付,
                   SUM(ib.self_pay) AS 自付金额
            FROM inpatient_billing ib
            GROUP BY ib.item_type
            ORDER BY 总金额 DESC
        """,
        "charts": [
            {"type": "pie", "title": "费用类型分布", "label": "费用类型", "value": "总金额"},
            {"type": "bar", "title": "各类费用对比", "x": "费用类型", "y": "总金额"},
        ]
    },

    # ===== 药品管理 =====
    "drug_stock": {
        "title": "药品库存查询",
        "sql": """
            SELECT m.generic_name AS 药品名称, m.category AS 分类,
                   m.specification AS 规格, mi.stock_qty AS 库存量,
                   mi.retail_price AS 零售价, mi.expiry_date AS 效期,
                   mi.batch_no AS 批号, s.supplier_name AS 供应商,
                   CASE WHEN mi.expiry_date <= DATE_ADD(CURDATE(), INTERVAL 3 MONTH) THEN '近效期' ELSE '正常' END AS 状态
            FROM medicine_inventory mi
            JOIN medicines m ON mi.medicine_id = m.id
            LEFT JOIN suppliers s ON mi.supplier_id = s.id
            ORDER BY mi.expiry_date ASC
        """,
        "charts": [
            {"type": "pie", "title": "药品分类库存", "label": "分类", "value": "库存量"},
        ]
    },
    "drug_rx": {
        "title": "处方用药分析",
        "sql": """
            SELECT m.generic_name AS 药品名称, m.category AS 分类,
                   COUNT(DISTINCT pi.prescription_id) AS 处方数,
                   SUM(pi.quantity) AS 总用量,
                   SUM(pi.amount) AS 总金额,
                   ROUND(AVG(pi.amount), 2) AS 平均金额
            FROM prescription_items pi
            JOIN medicines m ON pi.medicine_id = m.id
            GROUP BY m.generic_name, m.category
            ORDER BY 总金额 DESC
        """,
        "charts": [
            {"type": "pie", "title": "药品消耗占比", "label": "药品名称", "value": "总金额"},
            {"type": "bar", "title": "药品消耗金额TOP", "x": "药品名称", "y": "总金额"},
        ]
    },
    "drug_cons": {
        "title": "耗材管理",
        "sql": """
            SELECT c.item_name AS 耗材名称, c.category AS 分类,
                   c.stock_qty AS 库存量, c.unit_price AS 单价,
                   ROUND(c.stock_qty * c.unit_price, 2) AS 库存金额,
                   s.supplier_name AS 供应商,
                   CASE WHEN c.is_medical_ins = 1 THEN '医保' ELSE '自费' END AS 医保类型
            FROM consumables c
            LEFT JOIN suppliers s ON c.supplier_id = s.id
            ORDER BY 库存金额 DESC
        """,
        "charts": [
            {"type": "pie", "title": "耗材分类", "label": "分类", "value": "库存金额"},
        ]
    },

    # ===== 手术管理 =====
    "surg_record": {
        "title": "手术记录统计",
        "sql": """
            SELECT su.surgery_name AS 手术名称, su.surgery_type AS 手术等级,
                   d.dept_name AS 科室, st.name AS 主刀医生,
                   su.anesthesia_type AS 麻醉方式, su.outcome AS 结果,
                   su.surgery_cost AS 手术费用,
                   CASE WHEN su.is_emergency = 1 THEN '急诊' ELSE '择期' END AS 类型
            FROM surgeries su
            JOIN departments d ON su.department_id = d.id
            JOIN staff st ON su.surgeon_id = st.id
            ORDER BY su.surgery_cost DESC
        """,
        "charts": [
            {"type": "pie", "title": "手术等级分布", "label": "手术等级", "value": "手术费用"},
            {"type": "pie", "title": "手术结果", "label": "结果", "value": "手术费用"},
        ]
    },
    "exam_stat": {
        "title": "检查检验分析",
        "sql": """
            SELECT e.exam_type AS 检查类型, d.dept_name AS 科室,
                   st.name AS 开单医生,
                   COUNT(*) AS 次数,
                   SUM(CASE WHEN e.is_abnormal = 1 THEN 1 ELSE 0 END) AS 异常数,
                   ROUND(SUM(CASE WHEN e.is_abnormal = 1 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) AS 异常率,
                   SUM(e.exam_cost) AS 总费用
            FROM examinations e
            JOIN departments d ON e.department_id = d.id
            JOIN staff st ON e.order_doctor_id = st.id
            GROUP BY e.exam_type, d.dept_name, st.name
            ORDER BY 次数 DESC
        """,
        "charts": [
            {"type": "pie", "title": "检查类型分布", "label": "检查类型", "value": "次数"},
            {"type": "bar", "title": "各科室检查量", "x": "科室", "y": "次数"},
        ]
    },
    "equip_stat": {
        "title": "设备使用统计",
        "sql": """
            SELECT eu.equipment_name AS 设备名称, eu.equipment_type AS 设备类型,
                   d.dept_name AS 科室,
                   COUNT(*) AS 使用天数,
                   SUM(eu.usage_hours) AS 总使用时长,
                   SUM(eu.usage_count) AS 总使用次数,
                   SUM(CASE WHEN eu.is_breakdown = 1 THEN 1 ELSE 0 END) AS 故障次数
            FROM equipment_usage eu
            JOIN departments d ON eu.department_id = d.id
            GROUP BY eu.equipment_name, eu.equipment_type, d.dept_name
            ORDER BY 总使用次数 DESC
        """,
        "charts": [
            {"type": "pie", "title": "设备类型分布", "label": "设备类型", "value": "总使用次数"},
            {"type": "bar", "title": "设备使用TOP", "x": "设备名称", "y": "总使用次数"},
        ]
    },

    # ===== 财务分析 =====
    "fin_daily": {
        "title": "每日运营统计",
        "sql": """
            SELECT stat_date AS 日期,
                   outpatient_count AS 门诊量,
                   admission_count AS 入院人数,
                   discharge_count AS 出院人数,
                   surgery_count AS 手术量,
                   total_revenue AS 总收入,
                   total_cost AS 总成本,
                   net_profit AS 净利润,
                   ROUND(net_profit / total_revenue * 100, 2) AS 利润率,
                   bed_occupancy_rate AS 床位使用率,
                   patient_satisfaction AS 满意度
            FROM daily_operations
            WHERE department_id IS NULL
            ORDER BY stat_date ASC
        """,
        "charts": [
            {"type": "line", "title": "收入趋势", "x": "日期", "y": "总收入"},
            {"type": "line", "title": "门诊量趋势", "x": "日期", "y": "门诊量"},
        ]
    },
    "fin_perf": {
        "title": "科室绩效排名",
        "sql": """
            SELECT d.dept_name AS 科室, dp.stat_year AS 年份, dp.stat_month AS 月份,
                   dp.total_revenue AS 实际收入, dp.revenue_target AS 目标收入,
                   ROUND(dp.total_revenue / dp.revenue_target * 100, 2) AS 达成率,
                   dp.performance_score AS 绩效评分, dp.grade AS 等级,
                   dp.patient_satisfaction AS 满意度,
                   dp.mortality_rate AS 死亡率
            FROM department_performance dp
            JOIN departments d ON dp.department_id = d.id
            ORDER BY dp.stat_year, dp.stat_month, dp.performance_score DESC
        """,
        "charts": [
            {"type": "bar", "title": "科室绩效评分", "x": "科室", "y": "绩效评分"},
            {"type": "bar", "title": "收入达成率", "x": "科室", "y": "达成率"},
        ]
    },
    "fin_ins": {
        "title": "医保结算分析",
        "sql": """
            SELECT is2.insurance_type AS 医保类型, is2.status AS 结算状态,
                   COUNT(*) AS 笔数,
                   SUM(is2.total_cost) AS 总费用,
                   SUM(is2.insurance_pay) AS 医保支付,
                   SUM(is2.self_pay) AS 自付金额,
                   ROUND(AVG(is2.reimbursement_rate), 1) AS 平均报销比例
            FROM insurance_settlements is2
            GROUP BY is2.insurance_type, is2.status
            ORDER BY 总费用 DESC
        """,
        "charts": [
            {"type": "pie", "title": "医保类型分布", "label": "医保类型", "value": "总费用"},
            {"type": "bar", "title": "医保结算状态", "x": "结算状态", "y": "笔数"},
        ]
    },

    # ===== 质量监控 =====
    "qual_metric": {
        "title": "质量指标监控",
        "sql": """
            SELECT d.dept_name AS 科室, qm.metric_name AS 指标名称,
                   qm.metric_category AS 指标类别,
                   qm.metric_value AS 指标值, qm.unit AS 单位,
                   qm.target_value AS 目标值, qm.warning_value AS 预警值,
                   qm.status AS 状态, qm.period_type AS 统计周期
            FROM quality_metrics qm
            LEFT JOIN departments d ON qm.department_id = d.id
            ORDER BY qm.stat_date DESC, FIELD(qm.status, '超标', '预警', '关注', '正常')
        """,
        "charts": [
            {"type": "pie", "title": "指标状态分布", "label": "状态", "value": "指标值"},
            {"type": "bar", "title": "各科室指标达标", "x": "科室", "y": "指标值"},
        ]
    },
    "qual_sat": {
        "title": "患者满意度",
        "sql": """
            SELECT d.dept_name AS 科室,
                   AVG(qm.metric_value) AS 平均满意度,
                   MIN(qm.metric_value) AS 最低满意度,
                   MAX(qm.metric_value) AS 最高满意度,
                   COUNT(*) AS 指标数
            FROM quality_metrics qm
            JOIN departments d ON qm.department_id = d.id
            WHERE qm.metric_name LIKE '%满意度%'
            GROUP BY d.dept_name
            ORDER BY 平均满意度 DESC
        """,
        "charts": [
            {"type": "bar", "title": "科室满意度", "x": "科室", "y": "平均满意度"},
        ]
    },
}

# ========== 首页仪表板数据 ==========
DASHBOARD_CARDS = [
    {"title": "患者总数", "sql": "SELECT COUNT(*) AS v FROM patients", "icon": "fa-users", "color": "#3b82f6"},
    {"title": "今日门诊量", "sql": "SELECT IFNULL(SUM(outpatient_count),0) AS v FROM daily_operations WHERE stat_date = (SELECT MAX(stat_date) FROM daily_operations)", "icon": "fa-user-md", "color": "#8b5cf6"},
    {"title": "在院人数", "sql": "SELECT COUNT(*) AS v FROM inpatient_admissions WHERE status='在院'", "icon": "fa-bed", "color": "#06b6d4"},
    {"title": "今日手术量", "sql": "SELECT IFNULL(SUM(surgery_count),0) AS v FROM daily_operations WHERE stat_date = (SELECT MAX(stat_date) FROM daily_operations)", "icon": "fa-procedures", "color": "#10b981"},
    {"title": "总营收(万)", "sql": "SELECT ROUND(SUM(total_revenue)/10000, 1) AS v FROM daily_operations", "icon": "fa-yen-sign", "color": "#f59e0b"},
    {"title": "床位使用率", "sql": "SELECT ROUND(SUM(CASE WHEN status='占用' THEN 1 ELSE 0 END)/COUNT(*)*100,1) AS v FROM beds", "icon": "fa-chart-pie", "color": "#ef4444"},
    {"title": "员工人数", "sql": "SELECT COUNT(*) AS v FROM staff WHERE is_active=1", "icon": "fa-user-nurse", "color": "#ec4899"},
    {"title": "药品种类", "sql": "SELECT COUNT(*) AS v FROM medicines", "icon": "fa-pills", "color": "#14b8a6"},
]


# ========== 路由 ==========

@app.route("/")
def index():
    if "user" in session:
        return redirect(url_for("portal"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        # 简单验证
        if username in ("admin", "doctor", "nurse") and password == "admin123":
            session["user"] = username
            names = {"admin": "管理员", "doctor": "张医生", "nurse": "李护士"}
            session["user_name"] = names.get(username, username)
            return redirect(url_for("portal"))
        error = "用户名或密码错误"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/portal")
def portal():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("portal.html", user_name=session.get("user_name", "用户"))


@app.route("/admin")
def admin():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("admin.html", user_name=session.get("user_name", "用户"))


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    # 获取首页卡片数据
    cards = []
    for card in DASHBOARD_CARDS:
        try:
            row = query_one(card["sql"])
            value = row["v"] if row and row["v"] is not None else 0
            if isinstance(value, float):
                value = f"{value:,.1f}" if value < 10000 else f"{value:,.0f}"
            elif isinstance(value, int):
                value = f"{value:,}"
        except:
            value = "-"
        cards.append({
            "title": card["title"],
            "value": str(value),
            "icon": card["icon"],
            "color": card["color"],
        })

    return render_template(
        "dashboard.html",
        user_name=session.get("user_name", "用户"),
        cards=cards,
        top_nav=TOP_NAV,
    )


@app.route("/report/<report_id>")
def report(report_id):
    """通用报表渲染"""
    if "user" not in session:
        return redirect(url_for("login"))

    config = REPORT_SQL.get(report_id)
    if not config:
        return render_template("report_error.html", title="报表不存在", user_name=session.get("user_name", "用户"), top_nav=TOP_NAV)

    try:
        data = query_db(config["sql"])
    except Exception as e:
        data = []
        config["error"] = str(e)

    columns = list(data[0].keys()) if data else []
    charts = config.get("charts", [])

    # 把chart的中文key映射到数据
    chart_data = []
    for chart in charts:
        if chart["type"] == "pie":
            labels = [str(row.get(chart["label"], "")) for row in data]
            values = [float(row.get(chart["value"], 0)) for row in data]
            chart_data.append({
                "type": "pie", "title": chart["title"],
                "labels": labels, "values": values
            })
        elif chart["type"] == "bar":
            x_key = chart["x"]
            y_key = chart["y"]
            # 如果x_key是日期，取最近10条
            sorted_data = data[:15] if len(data) > 15 else data
            labels = [str(row.get(x_key, ""))[:10] for row in sorted_data]
            values = [float(row.get(y_key, 0) or 0) for row in sorted_data]
            chart_data.append({
                "type": "bar", "title": chart["title"],
                "labels": labels, "values": values
            })
        elif chart["type"] == "line":
            x_key = chart["x"]
            y_key = chart["y"]
            labels = [str(row.get(x_key, ""))[:10] for row in data]
            values = [float(row.get(y_key, 0) or 0) for row in data]
            chart_data.append({
                "type": "line", "title": chart["title"],
                "labels": labels, "values": values
            })

    return render_template(
        "report.html",
        report_id=report_id,
        title=config["title"],
        columns=columns,
        data=data,
        charts=chart_data,
        user_name=session.get("user_name", "用户"),
        top_nav=TOP_NAV,
        error=config.get("error"),
    )


# ========== API ==========
@app.route("/api/report-data/<report_id>")
def api_report_data(report_id):
    """API: 获取报表数据"""
    config = REPORT_SQL.get(report_id)
    if not config:
        return jsonify({"error": "not found"}), 404
    try:
        data = query_db(config["sql"])
        return jsonify({"columns": list(data[0].keys()) if data else [], "data": data, "total": len(data)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("=" * 50)
    print("  医疗运营数据决策平台")
    print("  访问地址: http://localhost:5000")
    print("  测试账号: admin / admin123")
    print("=" * 50)
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
