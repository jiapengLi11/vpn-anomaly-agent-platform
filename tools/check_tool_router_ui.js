async page => {
  await page.goto('http://127.0.0.1:18088/#/tasks/SYNTHETIC-DEMO-001');
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('tab',{name:'Agent 轨迹',exact:true}).click();
  await page.getByText('工具路由',{exact:true}).waitFor();
  if(await page.locator('.agent-trace article').count()!==6) throw new Error('Expected six workflow nodes');
  const router=page.locator('.agent-trace article').filter({hasText:'工具路由'});
  await router.getByText(/selected=2/).waitFor();
  await router.getByText(/rejected=0/).waitFor();
  await page.screenshot({path:'docs/assets/agent-trace.png',fullPage:true,animations:'disabled'});
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Mobile overflow');
  await page.screenshot({path:'docs/assets/agent-trace-mobile.png',fullPage:true,animations:'disabled'});
  const catalog=await page.evaluate(async()=>await (await fetch('http://127.0.0.1:8090/api/tools')).json());
  if(catalog.tools.map(tool=>tool.name).join(',')!=='knowledge.search,analyst.review') throw new Error('Unexpected catalog');
  return {nodes:6,router:'READY',tools:catalog.tools.map(tool=>tool.name)};
}
