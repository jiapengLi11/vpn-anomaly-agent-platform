async page => {
  // Explicit paid smoke test: requires the local API and server-side DS_API_KEY.
  await page.reload();
  await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('button',{name:'清除本机记录',exact:true}).click();
  const newChat=page.getByRole('button',{name:'新对话',exact:true});
  if(await newChat.isEnabled()) await newChat.click();
  await page.getByRole('checkbox',{name:'在本机保留会话 7 天'}).check();
  await page.getByRole('checkbox',{name:'使用本地 DeepSeek'}).check();
  await page.getByRole('textbox',{name:'输入你的问题',exact:true}).fill('开放集拒识是什么意思？');
  const responsePromise = page.waitForResponse(r => r.url().endsWith('/api/knowledge/answer/stream') && r.request().method() === 'POST', {timeout:80000});
  await page.getByRole('button',{name:'提问',exact:true}).click();
  await responsePromise;
  await page.locator('.stream-draft').waitFor({state:'visible',timeout:70000});
  await page.screenshot({path:'docs/assets/knowledge-qa-streaming.png',fullPage:true});
  await page.locator('.answer-meta').waitFor({timeout:70000});
  const result=await page.evaluate(()=>JSON.parse(localStorage.getItem('vpn-knowledge-conversations-v1')).sessions[0].turns[0].answer);
  if(result.status !== 'SUCCESS') throw new Error('Live answer did not succeed: '+result.status);
  await page.getByText('本次回答信息',{exact:true}).click();
  await page.getByRole('button',{name:/查看来源/}).first().click();
  await page.evaluate(() => window.scrollTo(0,0));
  await page.screenshot({path:'docs/assets/knowledge-qa-deepseek.png',fullPage:true});
  await page.reload();
  await page.locator('.answer-paragraph').first().waitFor();
  if(await page.locator('.qa-turn').count()!==1) throw new Error('Conversation did not restore');
  await page.setViewportSize({width:390,height:844});
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw new Error('Mobile overflow');
  await page.screenshot({path:'docs/assets/knowledge-qa-memory-mobile.png',fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'新对话',exact:true}).click();
  if(await page.locator('.qa-turn').count()) throw new Error('New conversation contains old turns');
  await page.getByRole('combobox',{name:'历史会话'}).selectOption({index:1});
  if(await page.locator('.qa-turn').count()!==1) throw new Error('Conversation switch failed');
  await page.getByRole('button',{name:'清除本机记录',exact:true}).click();
  await page.reload();
  if(await page.locator('.qa-turn').count()) throw new Error('Memory not deleted');
  console.log(JSON.stringify({status:result.status,model:result.model,firstDraftMs:result.firstDraftMs,elapsedMs:result.elapsedMs,usage:result.usage,paragraphCount:result.paragraphs.length,memoryChecks:'restore/switch/clear passed'}));
}
