import policy from '../../../shared/followup-policy.json' with { type: 'json' };

export function isFollowup(text) {
  const normalized=text.replace(/[\s，。！？、,.!?：:；;]/g,'').toLowerCase();
  return [normalized,...policy.prefixes.filter(p=>normalized.startsWith(p)).map(p=>normalized.slice(p.length))]
    .some(candidate=>policy.phrases.includes(candidate));
}

export function resolveQuery(question, history) {
  question=question.trim();
  if(!isFollowup(question)) return {query:question,strategy:'STANDALONE',policyVersion:policy.version};
  for(const message of history.slice(-8).reverse()) {
    if(message.role==='user' && message.content.trim() && !isFollowup(message.content)) {
      const anchor=message.content.trim().slice(0,500);
      return {query:anchor+' '+question,strategy:'FOLLOWUP_ANCHORED',anchor,policyVersion:policy.version};
    }
  }
  return {query:question,strategy:'NEEDS_CONTEXT',policyVersion:policy.version};
}
