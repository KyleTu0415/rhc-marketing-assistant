/* ===== RHC 规则配置中心 · 共享配置层 =====
 * 规则不写死在页面代码里：各模块统一从 localStorage 读取，
 * 配置中心（config.html）保存后全平台即时生效。
 * 真系统阶段仅需把读写层替换为飞书规则表/后端接口，页面逻辑不变。
 */
(function(){
  var STORAGE_KEY='rhc_rules_config_v1';

  var DEFAULT_CONFIG={
    grading:{
      label:'客户分级规则',
      status:{won:30,repeat:25,inquiry:15,new:5},
      type:{chain:20,hospital:10,other:0},
      region:{key:20,other:10},
      keyRegions:['美国','加拿大','英国','德国','法国','澳大利亚','瑞典','挪威','丹麦','荷兰','阿联酋','沙特','新加坡','马来西亚','泰国','越南','印尼','菲律宾'],
      width:{three:15,two:10,one:5},
      fresh:{d7:15,d14:8,stale:0},
      gradeA:80,
      gradeB:60
    },
    signal:{
      label:'商机信号规则',
      claimDailyLimit:5,
      releaseDays:14,
      aResponseHours:24,
      bResponseDays:3,
      noiseKeywords:'used, second hand, student, research paper, 二手, 求购一台, 论文'
    },
    mail:{
      label:'邮件写作规范',
      inquiry:'24小时内回复；客户每个问题逐条答全；主动附上规格、认证与图片；结尾明确下一步行动；专业简洁，不过度推销',
      development:'全文约120词；价值前置，不用冗长自我介绍；针对客户业务定制、避免群发感；只给一个明确行动号召；首封不带附件',
      followup:'按报价后3天/7天/14天节奏；每次跟进带来新价值（新案例、新认证、库存或促销信息）；不催促施压；顺带回应客户此前未答问题',
      quotation:'注明PI编号、总金额与报价有效期；重申贸易条款（FOB/CIF等）与付款方式；明确下一步（回签PI/支付定金）；说明PI附件内容'
    },
    news:{
      label:'新闻偏好',
      categories:['industry','market','competitor','product'],
      focusKeywords:'',
      blockKeywords:'',
      pageSize:12,
      sortBy:'date'
    }
  };

  function deepClone(o){return JSON.parse(JSON.stringify(o))}
  function deepMerge(base,over){
    if(!over||typeof over!=='object')return base;
    Object.keys(over).forEach(function(k){
      if(base[k]&&typeof base[k]==='object'&&!Array.isArray(base[k])&&over[k]&&typeof over[k]==='object'&&!Array.isArray(over[k])){
        deepMerge(base[k],over[k]);
      }else if(over[k]!==undefined&&over[k]!==null){
        base[k]=over[k];
      }
    });
    return base;
  }
  function getConfig(){
    var cfg=deepClone(DEFAULT_CONFIG);
    try{
      var saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||'null');
      if(saved)deepMerge(cfg,saved);
    }catch(e){/* 解析失败用默认 */}
    return cfg;
  }
  function saveConfig(cfg){
    localStorage.setItem(STORAGE_KEY,JSON.stringify(cfg));
  }
  function resetConfig(){
    localStorage.removeItem(STORAGE_KEY);
  }

  window.RHC_CONFIG={
    get:getConfig,
    save:saveConfig,
    reset:resetConfig,
    DEFAULT:DEFAULT_CONFIG,
    KEY:STORAGE_KEY
  };
})();
