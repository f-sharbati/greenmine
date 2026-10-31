'use client';
import {Children,createElement,isValidElement,useRef,type ReactNode,type ReactElement} from 'react';
import {motion,useInView,useIsPresent,useReducedMotion,type Variants} from 'motion/react';
import * as Tabs from '@radix-ui/react-tabs';

const animatedTags = {div:motion.div,span:motion.span,p:motion.p,h2:motion.h2,h3:motion.h3,strong:motion.strong,button:motion.button,small:motion.small,label:motion.label};
export function AnimatedCard({children,className='',as='section'}:{children:ReactNode;className?:string;as?:'section'|'div'}){
 const ref=useRef<HTMLElement>(null);
 const inView=useInView(ref,{once:true,amount:.12});
 const reduced=useReducedMotion();
 const box:Variants={hidden:{opacity:0,scale:reduced?1:.94,y:reduced?0:16},visible:{opacity:1,scale:1,y:0,transition:{duration:reduced?0:.48,ease:[.22,1,.36,1],delayChildren:reduced?0:.2,staggerChildren:reduced?0:.075}},exit:{opacity:0,scale:reduced?1:.96,y:reduced?0:-8,transition:{duration:reduced?0:.2,when:'afterChildren',staggerChildren:reduced?0:.025,staggerDirection:-1}}};
 const item:Variants={hidden:{opacity:0,y:reduced?0:10},visible:{opacity:1,y:0,transition:{duration:reduced?0:.36,ease:[.22,1,.36,1]}},exit:{opacity:0,y:reduced?0:-6,transition:{duration:reduced?0:.12}}};
 const Tag=as==='div'?motion.div:motion.section;
 return <Tag ref={ref as React.Ref<HTMLDivElement>} className={className} data-animated-card whileHover={reduced?undefined:{y:-4,transition:{duration:.25,ease:"easeOut"}}} initial="hidden" animate={inView?'visible':'hidden'} exit="exit" variants={box}>
 {Children.map(children,(child,index)=>{
   if(!isValidElement(child))return child;
   const element=child as ReactElement<Record<string,unknown>>;
   const tag=typeof element.type==='string'?animatedTags[element.type as keyof typeof animatedTags]:null;
   if(tag)return createElement(tag as React.ElementType,{...element.props,key:element.key??index,variants:item,'data-card-item':true});
   return <motion.div key={element.key??index} variants={item} data-card-item>{child}</motion.div>;
 })}
 </Tag>;
}

export function AnimatedPanel({value,children}:{value:string;children:ReactNode}){
 const present=useIsPresent();const reduced=useReducedMotion();
 return <Tabs.Content value={value} forceMount asChild><motion.div className="tab-panel" data-panel={value} inert={!present} aria-hidden={!present} initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0,transition:{duration:reduced?0:.16,when:'afterChildren'}}} transition={{duration:reduced?0:.2}}>{children}</motion.div></Tabs.Content>;
}
