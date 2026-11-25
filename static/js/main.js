const palette = {blue:'#4779E8', teal:'#2AB9A7', orange:'#F0A34A', red:'#E66B72', grid:'#EDF1F6', text:'#8B96A8'};
function chartBase(){
  return {responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false},tooltip:{backgroundColor:'#17243B',padding:12,titleFont:{family:'DM Sans'},bodyFont:{family:'DM Sans'}}}, scales:{x:{grid:{display:false},ticks:{color:palette.text,font:{family:'DM Sans'}}},y:{beginAtZero:true,grid:{color:palette.grid},ticks:{color:palette.text,precision:0,font:{family:'DM Sans'}}}}};
}
function makeLineChart(id, labels, values){
  const el=document.getElementById(id); if(!el) return;
  new Chart(el,{type:'line',data:{labels,datasets:[{data:values,borderColor:palette.blue,backgroundColor:'rgba(71,121,232,.10)',fill:true,tension:.38,pointRadius:4,pointBackgroundColor:'#fff',pointBorderWidth:2,pointBorderColor:palette.blue}]},options:chartBase()});
}
function makeDoughnutChart(id, values){
  const el=document.getElementById(id); if(!el) return;
  new Chart(el,{type:'doughnut',data:{labels:['Low','Medium','High'],datasets:[{data:values,backgroundColor:[palette.teal,palette.orange,palette.red],borderWidth:0,hoverOffset:5}]},options:{responsive:true,maintainAspectRatio:false,cutout:'72%',plugins:{legend:{display:false}}}});
}
function makeBarChart(id, labels, values){
  const el=document.getElementById(id); if(!el) return;
  new Chart(el,{type:'bar',data:{labels,datasets:[{data:values,backgroundColor:'#6B8FEA',borderRadius:6,maxBarThickness:42}]},options:{...chartBase(),scales:{...chartBase().scales,x:{...chartBase().scales.x,ticks:{...chartBase().scales.x.ticks,maxRotation:0}},y:chartBase().scales.y}}});
}
const search=document.getElementById('reportSearch');
if(search){search.addEventListener('input',()=>{const q=search.value.toLowerCase();document.querySelectorAll('#reportsTable tbody tr').forEach(row=>row.style.display=row.innerText.toLowerCase().includes(q)?'':'none');});}
document.querySelectorAll('.flash').forEach(el=>setTimeout(()=>{el.style.opacity='0';el.style.transform='translateY(-5px)';},4500));
