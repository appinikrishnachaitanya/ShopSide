"use client";
import {Check,Heart,MessageCircle,Sparkles,Users} from "lucide-react";

const products=[
  {name:"Navy shirt",type:"Outfit idea",sprite:"shirt"},
  {name:"Beige chinos",type:"Match the look",sprite:"chinos"},
  {name:"Desk lamp",type:"Workspace",sprite:"lamp"},
  {name:"Headphones",type:"Everyday",sprite:"headphones"},
];

export default function WelcomeIllustration(){
  return <div className="welcome-story" role="img" aria-label="Illustration of two friends sharing a shopping room, comparing products and choosing together">
    <div className="story-orbit story-orbit-one"/><div className="story-orbit story-orbit-two"/>
    <div className="story-topline"><span>THE SHOPPING ROOM</span><span>ILLUSTRATIVE PREVIEW</span></div>
    <div className="story-person story-person-alex"><div className="story-portrait story-portrait-alex"/><span><i/> Alex</span></div>
    <div className="story-bubble story-bubble-alex"><Heart size={15} fill="currentColor"/> Love this one</div>
    <div className="story-board"><div className="story-board-head"><div><Users size={16}/><strong>Our shopping room</strong></div><span><i/> 2 people here</span></div><div className="story-products">{products.map(product=><div className="story-product" key={product.name}><div className={`story-product-image story-product-${product.sprite}`}/><strong>{product.name}</strong><small>{product.type}</small></div>)}</div><div className="story-board-foot"><span><Sparkles size={14}/> ShopSide AI finds the options</span><span>YOU DECIDE TOGETHER</span></div></div>
    <div className="story-compare"><span>COMPARE TOGETHER</span><div><span className="story-mini-product story-mini-shirt"/><b>vs</b><span className="story-mini-product story-mini-chinos"/></div></div>
    <div className="story-bubble story-bubble-jamie"><MessageCircle size={15}/> Check the size</div>
    <div className="story-person story-person-jamie"><div className="story-portrait story-portrait-jamie"/><span><i/> Jamie</span></div>
    <div className="story-shared-pick"><Heart size={17} fill="currentColor"/><strong>Shared pick</strong><Check size={17}/></div>
  </div>
}
