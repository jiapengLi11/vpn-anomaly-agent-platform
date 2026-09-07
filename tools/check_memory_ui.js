async page => {
  // No paid request: verifies the already completed local answer.
  const result=await page.evaluate(()=>JSON.parse(localStorage.getItem('vpn-knowledge-conversations-v1')).sessions[0].turns[0].answer);
  if(result.status!=='SUCCESS') throw new Error('Expected completed answer');
  await page.getByText('本次回答信息',{exact:true}).click();
  await page.getByRole('button',{name:/查看来源/}).first().click();
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.screenshot({path:'docs/assets/knowledge-qa-deepseek.png',fullPage:true});
  await page.reload();
  await page.locator('.answer-paragraph').first().waitFor();
  if(await page.locator('.qa-turn').count()!==1) throw new Error('Restore failed');
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Mobile overflow');
  await page.screenshot({path:'docs/assets/knowledge-qa-memory-mobile.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'新对话',exact:true}).click();
  if(await page.locator('.qa-turn').count()) throw new Error('Conversation isolation failed');
  await page.getByRole('combobox',{name:'历史会话'}).selectOption({index:1});
  if(await page.locator('.qa-turn').count()!==1) throw new Error('Switch failed');
  await page.getByRole('button',{name:'清除本机记录',exact:true}).click();
  await page.reload();
  if(await page.locator('.qa-turn').count()) throw new Error('Deletion failed');
  console.log(JSON.stringify({status:result.status,model:result.model,firstDraftMs:result.firstDraftMs,elapsedMs:result.elapsedMs,usage:result.usage,memoryChecks:'restore/isolation/switch/clear passed'}));
}
