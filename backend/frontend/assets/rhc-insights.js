/* ============================================================
 * RHC 市场洞察新闻数据 —— 全系统共享
 * 首页(panel.html) / 新闻中心(insights.html) / 销售素材库(sales.html) 共用
 * 更新新闻时只需修改本文件，三处自动同步。
 *
 * category 取值：
 *   industry   行业趋势（宏观/市场规模/投资/政策）
 *   market     市场动态（区域需求/展会/认证/采购趋势）
 *   competitor 同行新闻（竞品及同行公司商业动作）
 *   product    产品技术（新品发布/技术突破）
 *
 * 前期手动维护；后期接入 RSS 自动抓取时，替换本数据源即可，
 * 各页面渲染逻辑无需改动。
 * ============================================================ */
var RHC_INSIGHT_DATA = [
  // ===== 行业趋势 =====
  {
    id: 'ins-001',
    category: 'industry',
    categoryLabel: '行业趋势',
    categoryColor: 'industry',
    title: 'AI重塑兽医行业：诊断影像、临床文档和远程监护技术投资激增',
    summary: 'Digitail融资2300万美元、Lupa Pets融资2000万美元，AI X光判读30秒内完成',
    date: '2026-08-19',
    url: 'https://ceo.ca/@GlobeNewswire/ai-is-reshaping-veterinary-medicine-investment-surges',
    regions: ['global'],
    products: []
  },
  {
    id: 'ins-002',
    category: 'industry',
    categoryLabel: '行业趋势',
    categoryColor: 'industry',
    title: '全球兽医医疗器械市场预计2030年达91亿美元',
    summary: 'CAGR 6.1%，北美占55.9%，AI诊断和POC检测驱动行业增长',
    date: '2026-08-25',
    url: 'https://www.globenewswire.com/news-release/2026/08/25/3350843/0/en/global-veterinary-medical-devices-market-to-reach-9-1-billion-by-2030.html',
    regions: ['global', 'north-america'],
    products: []
  },
  {
    id: 'ins-004',
    category: 'market',
    categoryLabel: '市场动态',
    categoryColor: 'market',
    title: '兽医影像数字化与AI辅助诊断加速，北美设备进入替换窗口',
    summary: '北美诊所设备平均更新周期约7年，2019年采购潮设备集中进入替换期',
    date: '2026-08-31',
    url: '',
    regions: ['north-america'],
    products: []
  },
  // ===== 市场动态 =====
  {
    id: 'ins-005',
    category: 'market',
    categoryLabel: '市场动态',
    categoryColor: 'market',
    title: '中东、东南亚兽医诊所扩容，基础设备批量需求上升',
    summary: '新院开业带动麻醉机、注射泵整套采购，适合以「新院配置清单」话题开发客户',
    date: '2026-08-31',
    url: '',
    regions: ['middle-east', 'southeast-asia'],
    products: ['anesthesia-workstation']
  },
  {
    id: 'ins-006',
    category: 'market',
    categoryLabel: '市场动态',
    categoryColor: 'market',
    title: '巴西宠物医疗市场持续增长，INMETRO认证新规即将实施',
    summary: '巴西将于2027年起要求所有进口兽用麻醉设备通过INMETRO认证，提前合规的企业将获得竞争优势',
    date: '2026-08-28',
    url: '',
    regions: ['brazil'],
    products: ['anesthesia-workstation', 'ventilator']
  },
  {
    id: 'ins-007',
    category: 'market',
    categoryLabel: '市场动态',
    categoryColor: 'market',
    title: '非洲 veterinary equipment 需求年增15%，中小型设备最受欢迎',
    summary: '撒哈拉以南非洲宠物医疗市场快速崛起，便携、性价比高的设备需求旺盛',
    date: '2026-08-22',
    url: '',
    regions: ['africa'],
    products: ['portable-anesthesia', 'monitor']
  },
  {
    id: 'ins-008',
    category: 'market',
    categoryLabel: '市场动态',
    categoryColor: 'market',
    title: 'VMX/WVC 2026：麻醉与监护一体化成主流展示方向',
    summary: '单品设备关注度下降，建议主推V5 Plus等麻醉监护一体化工作站方案',
    date: '2026-08-31',
    url: '',
    regions: ['global', 'north-america'],
    products: ['v5-plus']
  },
  // ===== 同行新闻 =====
  {
    id: 'ins-009',
    category: 'competitor',
    categoryLabel: '同行新闻',
    categoryColor: 'competitor',
    title: '中宠兽与日本尼普洛（NIPRO）达成全面战略合作',
    summary: '品牌授权、进口器械渠道运营、宠物医药联合研发、高端耗材国产化五大方向',
    date: '2026-08-01',
    url: '',
    regions: ['global', 'asia'],
    products: []
  },
  {
    id: 'ins-011',
    category: 'competitor',
    categoryLabel: '同行新闻',
    categoryColor: 'competitor',
    title: '睿视医疗与晓闻科技合作推进宠物CT智能化升级',
    summary: '融合AI影像辅助诊断模型，提升宠物CT临床诊疗能力',
    date: '2026-08-06',
    url: 'https://www.petdhw.com/show-52837.html',
    regions: ['china'],
    products: []
  },
  {
    id: 'ins-012',
    category: 'competitor',
    categoryLabel: '同行新闻',
    categoryColor: 'competitor',
    title: 'Mindray发布新款兽用麻醉工作站 VetAnesthesia Pro',
    summary: '集成触摸屏操控与低流量麻醉设计，瞄准中大型动物医院市场',
    date: '2026-08-15',
    url: '',
    regions: ['global', 'china'],
    products: ['anesthesia-workstation']
  },
  // ===== 产品技术 =====
  {
    id: 'ins-003',
    category: 'product',
    categoryLabel: '产品技术',
    categoryColor: 'product',
    title: 'IDEXX推出犬猫双物种心脏生物标志物检测',
    summary: '首个院内NT-proBNP快速检测，全球8万台Catalyst分析仪可用，10月北美上市',
    date: '2026-08-12',
    url: 'https://animalhealthnews.com/2026/08/12/idexx-launches-dual-species-point-of-care-cardiac-biomarker-test/',
    regions: ['north-america'],
    products: []
  },
  {
    id: 'ins-010',
    category: 'product',
    categoryLabel: '产品技术',
    categoryColor: 'product',
    title: 'Zoetis Portela猫骨关节炎止痛药在英国获批',
    summary: '首个长效抗NGF单克隆抗体，一次注射缓解猫OA疼痛长达3个月',
    date: '2026-07-30',
    url: 'https://news.zoetis.com/',
    regions: ['europe'],
    products: []
  }
];
