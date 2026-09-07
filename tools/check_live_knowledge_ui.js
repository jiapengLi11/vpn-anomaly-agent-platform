async page => {
  // Explicit paid smoke test: requires the local API and server-side DS_API_KEY.
  await page.reload();
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('checkbox',{name:'使用本地 DeepSeek'}).check();
  await page.getByRole('textbox',{name:'输入你的问题',exact:true}).fill('开放集拒识是什么意思？');
  const responsePromise = page.waitForResponse(r => r.url().endsWith('/api/knowledge/answer') && r.request().method() === 'POST', {timeout:80000});
  await page.getByRole('button',{name:'提问',exact:true}).click();
  const result = await (await responsePromise).json();
  if(result.status !== 'SUCCESS') throw new Error('Live answer did not succeed: '+result.status);
  await page.getByText('本次回答信息',{exact:true}).click();
  await page.getByRole('button',{name:/查看来源/}).first().click();
  await page.evaluate(() => window.scrollTo(0,0));
  await page.screenshot({path:'docs/assets/knowledge-qa-deepseek.png',fullPage:true});
  console.log(JSON.stringify({status:result.status,model:result.model,elapsedMs:result.elapsedMs,usage:result.usage,paragraphCount:result.paragraphs.length}));
}
