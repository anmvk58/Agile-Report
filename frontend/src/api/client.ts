const BASE=import.meta.env.VITE_API_URL ?? '/api';
export class ApiError extends Error{constructor(public status:number,message:string){super(message)}}
export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
 const token=localStorage.getItem('token'); const headers=new Headers(options.headers); if(options.body) headers.set('Content-Type','application/json'); if(token) headers.set('Authorization',`Bearer ${token}`);
 const response=await fetch(`${BASE}${path}`,{...options,headers});
 if(response.status===401){localStorage.removeItem('token'); if(location.pathname!='/login') location.href='/login'}
 if(!response.ok){let message='Có lỗi xảy ra'; try{const body=await response.json(); message=body.detail ?? body.errors?.[0]?.message ?? message}catch{} throw new ApiError(response.status,message)}
 if(response.status===204)return undefined as T; const type=response.headers.get('content-type')??''; return type.includes('json')?response.json() as Promise<T>:response.text() as T;
}
export const download=async(path:string,filename:string)=>{const token=localStorage.getItem('token');const r=await fetch(`${BASE}${path}`,{headers:{Authorization:`Bearer ${token}`}});if(!r.ok)throw new Error('Không thể tải file');const blob=await r.blob();const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=filename;a.click();URL.revokeObjectURL(a.href)};

