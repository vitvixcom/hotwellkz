/* Калькулятор стоимости СИП-дома HotWell.kz
   Движок и конфиг — строго по спецификации (calculatorEngine.ts). Валюта ₸. */
(function(){
"use strict";

// ---------- КОНФИГ ----------
var BASE_PRICES=[
 {min:10,max:24,price:124781},{min:25,max:49,price:101895},{min:50,max:74,price:96589},
 {min:75,max:99,price:84482},{min:100,max:149,price:67661},{min:150,max:199,price:57670},
 {min:200,max:249,price:53309},{min:250,max:299,price:48950},{min:300,max:349,price:48400},
 {min:350,max:399,price:47300},{min:400,max:499,price:46200},{min:500,max:1500,price:45100}
];
var FOUNDATION=[
 {label:"Ж/Б ленточ. Зас. ПГС, стяжка 80мм. Выс 40см",value:7691},
 {label:"Без фундамента",value:0},
 {label:"СИП пол (на сваях)",value:23572},
 {label:"Баллочное перекрытие (балки 40х190 + ОСБ 18мм)",value:7691},
 {label:"Фундамент на металлических сваях",value:34178},
 {label:"Демонтаж кровли",value:3884},
 {label:"Демонтаж кровли + сейсмопояс + балочное перекрытие",value:11574},
 {label:"Демонтаж кровли + балочное перекрытие",value:7691},
 {label:"Демонтаж кровли + демонтаж этажа",value:7691},
 {label:"Ж/Б ленточный, Выс 50см",value:10722},
 {label:"Ж/Б ленточный, Выс 100см",value:14743},
 {label:"Ж/Б ленточный, Выс 150см",value:21798},
 {label:"Монтаж межэтажного перекрытия",value:7691},
 {label:"Ж/Б ленточный, Выс 60 см",value:11535},
 {label:"Ж/Б ленточный, перепад Выс 250см",value:37334}
];
var FLOORS=[{label:"1 этаж",value:"1",addition:7295},{label:"2 этажа",value:"2",addition:1619},{label:"3 этажа",value:"3",addition:0}];
var FLOOR_TYPE=[{label:"Полноценный",addition:0},{label:"Мансардный",addition:7736}];
var HEIGHTS=[
 {label:"2,5 м",value:2.5,addition:0},{label:"2,8 м",value:2.8,addition:3798},{label:"2,9 м",value:2.9,addition:4233},
 {label:"3,0 м",value:3.0,addition:5290},{label:"3,5 м",value:3.5,addition:8241},{label:"4,0 м",value:4.0,addition:12514},
 {label:"4,5 м",value:4.5,addition:16786},{label:"5,0 м",value:5.0,addition:21058},{label:"5,5 м",value:5.5,addition:25328},{label:"6,0 м",value:6.0,addition:29604}
];
var THICKNESS=[{label:"SIP-163 мм",value:163,addition:0},{label:"SIP-174 мм",value:174,addition:0},{label:"SIP-214 мм",value:214,addition:0},{label:"SIP-219 мм",value:219,addition:0},{label:"SIP-224 мм",value:224,addition:0}];
var P_PROFILE={label:"Профиль + гипсокартон + мин. вата, толщина 100 мм",addition:0};
var P_BRUS={label:"Брус + гипсокартон + мин. вата, толщина 100 мм",addition:0};
var P_NONE={label:"Без перегородок",addition:-2432};
var PARTITIONS={
 height_2_5:[P_PROFILE,P_BRUS,P_NONE,{label:"СИП-панели 163 мм (цельная панель 2,5 м)",addition:7768}],
 height_2_8:[P_PROFILE,P_BRUS,P_NONE,{label:"СИП-панели 163 мм (цельная панель 2,8 м)",addition:10203}],
 height_2_9:[P_PROFILE,P_BRUS,P_NONE,{label:"СИП-панели 163 мм, высота 2,9 м",addition:10867}],
 height_3_0:[P_PROFILE,P_BRUS,P_NONE,{label:"СИП-панели 163 мм, высота 3,0 м",addition:11108}],
 height_3_5:[P_PROFILE,P_BRUS,P_NONE,{label:"СИП-панели 163 мм, высота 3,5 м",addition:13968}],
 height_4_0:[P_PROFILE,P_BRUS,P_NONE,{label:"СИП-панели 163 мм, высота 4,0 м",addition:17065}]
};
function partKey(h){return h===2.8?"height_2_8":h===2.9?"height_2_9":h===3.0?"height_3_0":h===3.5?"height_3_5":h===4.0?"height_4_0":"height_2_5";}
var CEILING=[{label:"Потолок утеплённый (пенополистирол 145 мм)",addition:0},{label:"Без утепления потолка",addition:-1758},{label:"СИП-потолок (перекрытие)",addition:25221}];
var ROOF=[
 {label:"1-скатная",addition:0},
 {label:"1-скатная в стиле Хайтек (стропильная система + металлочерепица)",addition:1616},
 {label:"2-скатная (строп. сист. + металлочерепица)",addition:1616},
 {label:"4-скатная (конверт, для двухэтажного дома)",addition:4723,floors:"2"},
 {label:"4-скатная (конверт, для одноэтажного дома)",addition:7085,floors:"1"},
 {label:"Без крыши и без потолка",addition:-6507},
 {label:"Без крыши",addition:-6507},
 {label:"1-скатная (строп. сист. без металлочерепицы)",addition:-1108},
 {label:"2-скатная (строп. сист. без металлочерепицы)",addition:-601},
 {label:"1-скатная мансардная (СИП + металлочерепица)",addition:5630},
 {label:"2-скатная мансардная (СИП + металлочерепица)",addition:10352},
 {label:"4-скатная мансардная (СИП + металлочерепица)",addition:16621}
];
var SHAPE=[{label:"Простая форма",addition:0},{label:"Сложная форма",addition:4676}];
var ADD_WORKS=[
 {label:"Без дополнительных работ",addition:0},
 {label:"Обшивка СИП стен внутри дома гипсокартоном",addition:10362},
 {label:"Обшивка СИП стен внутри дома гипсокартоном + электромонтаж",addition:17152},
 {label:"Отделка фасада пеноплекс + мюнхенская штукатурка",addition:16080},
 {label:"Отделка фасада пеноплексом",addition:8037},
 {label:"Отделка фундамента пеноплексом",addition:2420},
 {label:"Отделка фасада и фундамента пеноплексом",addition:10480}
];
var DELIVERY=[
 {label:"Выберите город доставки",price:0},
 {label:"Алматы",price:0},
 {label:"Абай",price:550000},
 {label:"Аксай",price:1220000},
 {label:"Аксу",price:670000},
 {label:"Актау",price:1300000},
 {label:"Актобе",price:1000000},
 {label:"Аркалык",price:665000},
 {label:"Астана",price:646350},
 {label:"Атбасар",price:700000},
 {label:"Атырау",price:1215000},
 {label:"Аягоз",price:360000},
 {label:"Балхаш",price:300000},
 {label:"Булаево",price:840000},
 {label:"Есик",price:50000},
 {label:"Жанаозен",price:1180000},
 {label:"Жаркент",price:165000},
 {label:"Жезказган",price:726000},
 {label:"Жетысай",price:465000},
 {label:"Зайсан",price:475000},
 {label:"Караганда",price:550000},
 {label:"Каратау",price:315000},
 {label:"Каркаралинск",price:425000},
 {label:"Каскелен",price:50000},
 {label:"Кентау",price:415000},
 {label:"Кокшетау",price:715000},
 {label:"Конаев",price:50000},
 {label:"Костанай",price:900000},
 {label:"Курчатов",price:515000},
 {label:"Кызылорда",price:530000},
 {label:"Лисаковск",price:905000},
 {label:"Макинск",price:700000},
 {label:"Павлодар",price:670000},
 {label:"Петропавловск",price:800000},
 {label:"Приозёрск",price:245000},
 {label:"Риддер",price:570000},
 {label:"Рудный",price:900000},
 {label:"Сарань",price:550000},
 {label:"Сарыагаш",price:405000},
 {label:"Сатпаев",price:726000},
 {label:"Семей",price:527000},
 {label:"Сергеевка",price:835000},
 {label:"Серебрянск",price:530000},
 {label:"Степногорск",price:660000},
 {label:"Степняк",price:705000},
 {label:"Талгар",price:50000},
 {label:"Талдыкорган",price:125000},
 {label:"Тараз",price:240000},
 {label:"Текели",price:145000},
 {label:"Темир",price:1005000},
 {label:"Темиртау",price:488000},
 {label:"Туркестан",price:395000},
 {label:"Уральск",price:1285000},
 {label:"Усть-Каменогорск",price:510000},
 {label:"Ушарал",price:275000},
 {label:"Форт-Шевченко",price:1300000},
 {label:"Хромтау",price:975000},
 {label:"Шалкар",price:875000},
 {label:"Шар",price:475000},
 {label:"Шахтинск",price:550000},
 {label:"Шу",price:155000},
 {label:"Шымкент",price:330000},
 {label:"Экибастуз",price:612000}
];
// ---- Контекст доставки: город с лендинга запоминается и добавляет доставку к ценам ----
window.HW_DELIVERY = DELIVERY;
(function(){
  function priceFor(city){ for(var i=0;i<DELIVERY.length;i++) if(DELIVERY[i].label===city) return DELIVERY[i].price; return 0; }
  var CITY=null;
  try{
    if(window.__HW_CITY__ && DELIVERY.some(function(x){return x.label===window.__HW_CITY__;}))
      sessionStorage.setItem('hw_city', window.__HW_CITY__);
    CITY=sessionStorage.getItem('hw_city');
  }catch(e){}
  var CP = CITY?priceFor(CITY):0;
  function truckN(a){ return Math.max(1, Math.ceil((a||0)/150)); }
  function grp(n){ return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g,' '); }
  window.HWctx = {
    city:function(){ return CP>0 ? CITY : null; },
    priceFor:priceFor, truckN:truckN,
    cost:function(a){ return CP>0 ? truckN(a)*CP : 0; },
    clear:function(){ try{ sessionStorage.removeItem('hw_city'); }catch(e){} CITY=null; CP=0; }
  };
  // Добавляем доставку к статичным ценам (карточки проектов на главной/лендингах,
  // и крупная цена на странице проекта) + пометку. Только при активном городе.
  function applyStatic(){
    if(CP<=0) return;
    // 1) страница проекта — крупная цена
    var pgp=document.querySelector('.pg-price'), dr=document.getElementById('calcDrawer');
    if(pgp && dr){
      var area=parseFloat(dr.getAttribute('data-area')||'0');
      var base=parseInt((pgp.textContent||'').replace(/[^0-9]/g,''),10)||0;
      if(base>0 && area>0){
        pgp.innerHTML='от '+grp(base+truckN(area)*CP)+' ₸';
        if(!document.querySelector('.pg-deliv')){
          var note=document.createElement('div'); note.className='pg-deliv';
          note.innerHTML='🚚 включена доставка до г. '+CITY;
          pgp.parentNode.insertBefore(note, pgp.nextSibling);
        }
      }
    }
    // 2) карточки проектов (Топ-проекты, Построенные дома и т.п.).
    // Площадь: data-area → span меты «X м²» (изолированно) → номер модели «Б-168».
    function cardArea(c){
      var a=parseFloat(c.getAttribute('data-area'))||0; if(a>0) return a;
      var re=/(\d+)\s*(?:м²|кв\.?\s*м)/i, mm, v;
      var sp=c.querySelectorAll('.meta span, .meta b');   // изолированно, без склейки с названием
      for(var j=0;j<sp.length;j++){
        mm=(sp[j].textContent||'').match(re);
        if(mm){ v=parseInt(mm[1],10); if(v>=10&&v<=2000) return v; }
      }
      var h=c.querySelector('h3'), t=h?(h.textContent||''):'';   // площадь из названия
      mm=t.match(/«[A-Za-zА-Яа-я]-(\d+)/);
      if(mm){ v=parseInt(mm[1],10); if(v>=10&&v<=2000) return v; }
      mm=t.match(re);
      if(mm){ v=parseInt(mm[1],10); if(v>=10&&v<=2000) return v; }
      return 0;
    }
    var cards=document.querySelectorAll('.project');
    for(var i=0;i<cards.length;i++){
      var c=cards[i];
      if(c.getAttribute('data-hwd') || (c.closest && c.closest('#catGrid'))) continue;
      var pr=c.querySelector('.price'); if(!pr) continue;
      var b=parseInt((pr.textContent||'').replace(/[^0-9]/g,''),10)||0; if(b<=0) continue;
      var a=cardArea(c); if(a<=0) continue;
      pr.innerHTML='от '+grp(b+truckN(a)*CP)+' ₸';
      c.setAttribute('data-hwd','1');
      if(!c.querySelector('.price-deliv')){
        var nn=document.createElement('div'); nn.className='price-deliv';
        nn.textContent='🚚 с доставкой до г. '+CITY;
        pr.parentNode.insertBefore(nn, pr.nextSibling);
      }
    }
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', applyStatic);
  else applyStatic();
})();
var COST_BREAKDOWN={foundation:0.14,houseKit:0.71,assembly:0.15};
var AREA_LIMITS={min:10,max:1500};
var MULT=1.1;

function findL(arr,l){for(var i=0;i<arr.length;i++)if(arr[i].label===l)return arr[i];return null;}
function basePrice(a){for(var i=0;i<BASE_PRICES.length;i++)if(a>=BASE_PRICES[i].min&&a<=BASE_PRICES[i].max)return BASE_PRICES[i].price;return 0;}
function trucks(a){return Math.ceil(a/150);}

// ---------- ДВИЖОК ----------
function calc(p){
 var a=p.area, z={fundamentCost:0,kitCost:0,assemblyCost:0,customWorksCost:0,total:0,pricePerSqm:0,deliveryCost:0};
 if(!a||a<AREA_LIMITS.min||a>AREA_LIMITS.max)return z;
 var base=basePrice(a);
 var f=findL(FOUNDATION,p.foundation); var foundAdd=f?(f.value!=null?f.value:(f.addition||0)):0;
 var floorsAdd=(findL(FLOORS,p.floors)||{}).addition||0;
 var f1t=p.floors==="1 этаж"?((findL(FLOOR_TYPE,p.firstFloorType||"")||{}).addition||0):0;
 var f2key=p.floors==="3 этажа"?"Полноценный":(p.secondFloorType||"");
 var f2t=(p.floors==="2 этажа"||p.floors==="3 этажа")?((findL(FLOOR_TYPE,f2key)||{}).addition||0):0;
 var f3t=p.floors==="3 этажа"?((findL(FLOOR_TYPE,p.thirdFloorType||"")||{}).addition||0):0;
 function h(v){if(v==null)return 0;for(var i=0;i<HEIGHTS.length;i++)if(HEIGHTS[i].value===v)return HEIGHTS[i].addition||0;return 0;}
 function t(v){if(v==null)return 0;for(var i=0;i<THICKNESS.length;i++)if(THICKNESS[i].value===v)return THICKNESS[i].addition||0;return 0;}
 var grp=PARTITIONS[partKey(p.firstFloorHeight)]||PARTITIONS.height_2_5;
 var partition=((findL(grp,p.partitionType)||{}).addition)||0;
 var ceiling=((findL(CEILING,p.ceiling)||{}).addition)||0;
 var roof=0;for(var i=0;i<ROOF.length;i++){var o=ROOF[i];if(o.label===p.roofType&&(!o.floors||o.floors===String(p.floors).charAt(0))){roof=o.addition||0;break;}}
 var shape=((findL(SHAPE,p.houseShape)||{}).addition)||0;

 var pricePerSqm=base+floorsAdd+h(p.firstFloorHeight)+h(p.secondFloorHeight)+h(p.thirdFloorHeight)
   +t(p.firstFloorThickness)+t(p.secondFloorThickness)+t(p.thirdFloorThickness)
   +f1t+f2t+f3t+foundAdd+roof+shape+partition+ceiling;

 var baseTotal=Math.round(pricePerSqm*a);
 var standardAdd=!p.useCustomWorks?Math.round(((findL(ADD_WORKS,p.additionalWorks)||{}).addition||0)*a):0;
 var customTotal=0;
 if(p.useCustomWorks&&p.customWorks)for(var k=0;k<p.customWorks.length;k++){var pr=parseFloat(String(p.customWorks[k].price).replace(/\s/g,""))||0;customTotal+=pr;}
 var deliveryCost=0;
 if(p.deliveryCity){var d=findL(DELIVERY,p.deliveryCity);if(d&&d.price&&p.deliveryCity!=="Выберите город доставки")deliveryCost=trucks(a)*d.price;}

 var cfb=baseTotal+standardAdd;
 // Без фундамента: строку фундамента убираем, его долю (14%) распределяем
 // на домокомплект и сборку пропорционально (71:15) — сумма остаётся прежней.
 var noFound=(f&&f.label==="Без фундамента")||foundAdd===0;
 var fund,kit,asm;
 if(noFound){
  fund=0;
  var kitShare=COST_BREAKDOWN.houseKit/(COST_BREAKDOWN.houseKit+COST_BREAKDOWN.assembly);
  kit=Math.round(cfb*kitShare); asm=cfb-kit;
 }else{
  fund=Math.round(cfb*COST_BREAKDOWN.foundation); kit=Math.round(cfb*COST_BREAKDOWN.houseKit); asm=Math.round(cfb*COST_BREAKDOWN.assembly);
 }
 var ap=function(x){return Math.round(x*MULT);};
 return {
  fundamentCost:ap(fund), kitCost:ap(kit), assemblyCost:ap(asm), noFoundation:noFound,
  customWorksCost:customTotal,
  total:ap(baseTotal+standardAdd+deliveryCost)+customTotal,
  pricePerSqm:ap(Math.round(pricePerSqm)),
  deliveryCost:ap(deliveryCost)
 };
}

// ---------- UI ----------
function fmt(n){return (Math.round(n)+"").replace(/\B(?=(\d{3})+(?!\d))/g,' ')+" ₸";}
function el(tag,cls,html){var e=document.createElement(tag);if(cls)e.className=cls;if(html!=null)e.innerHTML=html;return e;}
function opt(v,t){var o=document.createElement('option');o.value=v;o.textContent=t;return o;}

var form=document.getElementById('calcForm'); if(!form)return;
var resultBox=document.getElementById('calcResult');

function field(label,id,pro){
 var d=el('div','cfield'+(pro?' cpro':''));
 d.appendChild(el('label',null,label));
 var c; if(id==='cArea'){c=document.createElement('input');c.type='number';c.min=10;c.max=1500;c.value=100;c.placeholder='например, 100';}
 else {c=document.createElement('select');}
 c.id=id; d.appendChild(c); form.appendChild(d); return c;
}
function fill(sel,arr,getV,getT,def){sel.innerHTML='';arr.forEach(function(o){sel.appendChild(opt(getV(o),getT(o)));});if(def!=null)sel.value=def;}

// строим поля
var iArea=field('Площадь дома, м²','cArea');
var iFloors=field('Этажность','cFloors');
var iFound=field('Фундамент','cFoundation');
var floorsWrap=el('div','cpro'); floorsWrap.id='cFloorsBlocks'; form.appendChild(floorsWrap); // pro: поэтажные параметры
var iRoof=field('Тип крыши','cRoof');
var iPart=field('Перегородки','cPartition',true);
var iCeil=field('Потолок','cCeiling',true);
var iShape=field('Форма дома','cShape',true);
var iAdd=field('Дополнительные работы','cAdd');
// ручные работы (pro)
var customWrap=el('div','cpro'); customWrap.id='cCustomWrap';
var customToggle=el('label','calc-check'); var ct=document.createElement('input');ct.type='checkbox';ct.id='cUseCustom';
customToggle.appendChild(ct);customToggle.appendChild(el('span',null,' Ввести работы вручную (суммы ₸)'));
customWrap.appendChild(customToggle);
var customList=el('div',null);customList.id='cCustomList';customWrap.appendChild(customList);
var addBtn=el('button','btn btn--outline','+ Добавить работу');addBtn.type='button';addBtn.style.marginTop='8px';customWrap.appendChild(addBtn);
form.appendChild(customWrap);
var iDelivery=field('Город доставки','cDelivery');
// НДС (pro)
var vatWrap=el('label','calc-check cpro');var vat=document.createElement('input');vat.type='checkbox';vat.id='cVat';
vatWrap.appendChild(vat);vatWrap.appendChild(el('span',null,' Показать с учётом НДС 16%'));form.appendChild(vatWrap);

fill(iFloors,FLOORS,function(o){return o.label;},function(o){return o.label;},'1 этаж');
fill(iFound,FOUNDATION,function(o){return o.label;},function(o){return o.label;},'Ж/Б ленточ. Зас. ПГС, стяжка 80мм. Выс 40см');
fill(iCeil,CEILING,function(o){return o.label;},function(o){return o.label;},CEILING[0].label);
fill(iShape,SHAPE,function(o){return o.label;},function(o){return o.label;},SHAPE[0].label);
fill(iAdd,ADD_WORKS,function(o){return o.label;},function(o){return o.label;},ADD_WORKS[0].label);
fill(iDelivery,DELIVERY,function(o){return o.label;},function(o){return o.label;},DELIVERY[0].label);
// если пришли с городской страницы — подставляем этот город в доставку
try{ var _hc=window.HWctx&&window.HWctx.city&&window.HWctx.city(); if(_hc) iDelivery.value=_hc; }catch(e){}

var DEFAULT_ROOF="2-скатная (строп. сист. + металлочерепица)"; // крыша по умолчанию
function buildRoof(){
 var fl=String((findL(FLOORS,iFloors.value)||{}).value||'1');
 var list=ROOF.filter(function(o){return !o.floors||o.floors===fl;});
 var cur=iRoof.value;
 fill(iRoof,list,function(o){return o.label;},function(o){return o.label;});
 var has=function(v){return [].slice.call(iRoof.options).some(function(o){return o.value===v;});};
 if(has(cur))iRoof.value=cur; else if(has(DEFAULT_ROOF))iRoof.value=DEFAULT_ROOF; else iRoof.value=list[0].label;
}
function buildPartition(){
 var h=parseFloat((document.getElementById('cH1')||{}).value)||2.5;
 var grp=PARTITIONS[partKey(h)]||PARTITIONS.height_2_5;
 var cur=iPart.value;
 fill(iPart,grp,function(o){return o.label;},function(o){return o.label;});
 if([].slice.call(iPart.options).some(function(o){return o.value===cur;}))iPart.value=cur; else iPart.value=grp[0].label;
}
function buildFloors(){
 floorsWrap.innerHTML='';
 var n=parseInt((findL(FLOORS,iFloors.value)||{}).value||'1',10);
 for(var i=1;i<=n;i++){
  var box=el('div','cfloor');box.appendChild(el('div','cfloor-h','Этаж '+i));
  // тип
  var dt=el('div','cfield');dt.appendChild(el('label',null,'Тип этажа'));var st=document.createElement('select');st.id='cT'+i;
  fill(st,FLOOR_TYPE,function(o){return o.label;},function(o){return o.label;},'Полноценный');
  if(i===3){st.value='Полноценный';st.disabled=true;}
  dt.appendChild(st);box.appendChild(dt);
  // высота
  var dh=el('div','cfield');dh.appendChild(el('label',null,'Высота этажа'));var sh=document.createElement('select');sh.id='cH'+i;
  fill(sh,HEIGHTS,function(o){return o.value;},function(o){return o.label;},'2.5');box.appendChild((function(){dh.appendChild(sh);return dh;})());
  // толщина
  var dk=el('div','cfield');dk.appendChild(el('label',null,'Толщина SIP'));var sk=document.createElement('select');sk.id='cK'+i;
  fill(sk,THICKNESS,function(o){return o.value;},function(o){return o.label;},'163');dk.appendChild(sk);box.appendChild(dk);
  floorsWrap.appendChild(box);
 }
 // навесим слушатели на высоту 1 этажа → перегородки
 var h1=document.getElementById('cH1'); if(h1)h1.addEventListener('change',function(){buildPartition();recalc();});
}
function addCustomRow(){
 var row=el('div','ccustom-row');
 var n=document.createElement('input');n.type='text';n.placeholder='Наименование';n.className='cc-name';
 var p=document.createElement('input');p.type='text';p.placeholder='Стоимость, ₸';p.className='cc-price';
 var rm=el('button','cc-del','×');rm.type='button';
 rm.addEventListener('click',function(){row.remove();recalc();});
 p.addEventListener('input',recalc);
 row.appendChild(n);row.appendChild(p);row.appendChild(rm);customList.appendChild(row);
}

function readInput(){
 var floors=iFloors.value;
 var g=function(id){var e=document.getElementById(id);return e?e.value:null;};
 var customWorks=[];
 if(ct.checked){[].slice.call(customList.querySelectorAll('.ccustom-row')).forEach(function(r){
   customWorks.push({name:r.querySelector('.cc-name').value,price:r.querySelector('.cc-price').value});});}
 return {
  area:parseFloat(iArea.value),
  foundation:iFound.value, floors:floors,
  firstFloorType:g('cT1'), secondFloorType:g('cT2'), thirdFloorType:g('cT3'),
  firstFloorHeight:parseFloat(g('cH1')||2.5), secondFloorHeight:g('cH2')?parseFloat(g('cH2')):undefined, thirdFloorHeight:g('cH3')?parseFloat(g('cH3')):undefined,
  firstFloorThickness:parseFloat(g('cK1')||163), secondFloorThickness:g('cK2')?parseFloat(g('cK2')):undefined, thirdFloorThickness:g('cK3')?parseFloat(g('cK3')):undefined,
  partitionType:iPart.value, ceiling:iCeil.value, roofType:iRoof.value, houseShape:iShape.value,
  additionalWorks:iAdd.value, useCustomWorks:ct.checked, customWorks:customWorks,
  deliveryCity:iDelivery.value
 };
}

function recalc(){
 var inp=readInput();
 var r=calc(inp);
 if(!resultBox)return;
 if(!r.total){resultBox.innerHTML='<div class="calc-empty">Введите площадь от 10 до 1500 м² — расчёт появится здесь.</div>';return;}
 var rows='';
 if(r.noFoundation){
  rows+='<div class="cr-row"><span>🏠 Домокомплект (83%)</span><b>'+fmt(r.kitCost)+'</b></div>';
  rows+='<div class="cr-row"><span>⚒️ Сборка (17%)</span><b>'+fmt(r.assemblyCost)+'</b></div>';
 }else{
  rows+='<div class="cr-row"><span>🏗️ Фундамент (14%)</span><b>'+fmt(r.fundamentCost)+'</b></div>';
  rows+='<div class="cr-row"><span>🏠 Домокомплект (71%)</span><b>'+fmt(r.kitCost)+'</b></div>';
  rows+='<div class="cr-row"><span>⚒️ Сборка (15%)</span><b>'+fmt(r.assemblyCost)+'</b></div>';
 }
 if(r.customWorksCost>0)rows+='<div class="cr-row"><span>🛠️ Доп. работы</span><b>'+fmt(r.customWorksCost)+'</b></div>';
 if(r.deliveryCost>0)rows+='<div class="cr-row"><span>🚚 Доставка ('+inp.deliveryCity+')</span><b>'+fmt(r.deliveryCost)+'</b></div>';
 var vatLine='';
 if(vat.checked){var vatAmount=Math.round(r.total/1.16*0.16);vatLine='<div class="cr-row cr-sub"><span>в т.ч. НДС 16%</span><b>'+fmt(vatAmount)+'</b></div>';}
 var wa="https://wa.me/77477434343?text="+encodeURIComponent(
   "Здравствуйте! Рассчитал на сайте дом из СИП-панелей:\n"+
   "Площадь: "+inp.area+" м², "+inp.floors+"\n"+
   "Цена за м²: "+fmt(r.pricePerSqm)+"\n"+
   "Итого: "+fmt(r.total)+" без НДС\n"+
   "Хочу уточнить смету.");
 resultBox.innerHTML=
   '<div class="cr-ppsqm">'+fmt(r.pricePerSqm)+' <span>за 1 м²</span></div>'+
   '<div class="cr-list">'+rows+'</div>'+
   '<div class="cr-total"><span>Итого</span><b>'+fmt(r.total)+'</b></div>'+
   '<div class="cr-note">'+(vat.checked?vatLine:'<span class="cr-vat">цена без НДС</span>')+'</div>'+
   '<a href="'+wa+'" target="_blank" rel="noopener" class="btn btn--wa btn--block cr-cta"><svg width="20"><use href="#i-wa"/></svg> Отправить в WhatsApp</a>'+
   '<p class="cr-disc">Предварительный расчёт. Точную смету подготовим после согласования (онлайн за 5 минут).</p>';
}

// события
iFloors.addEventListener('change',function(){buildFloors();buildRoof();buildPartition();recalc();});
[iArea,iFound,iRoof,iPart,iCeil,iShape,iAdd,iDelivery,vat].forEach(function(e){e.addEventListener('input',recalc);});
ct.addEventListener('change',function(){customList.style.display=ct.checked?'':'none';addBtn.style.display=ct.checked?'':'none';if(ct.checked&&!customList.children.length)addCustomRow();recalc();});
addBtn.addEventListener('click',function(){addCustomRow();recalc();});

// pro-режим
var pro=document.getElementById('calcPro');
function applyPro(){form.classList.toggle('pro',pro.checked);recalc();}
if(pro)pro.addEventListener('change',applyPro);

// инициализация
buildFloors();buildRoof();buildPartition();
customList.style.display='none';addBtn.style.display='none';
recalc();
})();
