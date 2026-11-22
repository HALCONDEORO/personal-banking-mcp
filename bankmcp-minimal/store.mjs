// New hardening layer. Cipher key is injected by a future OS-protected owner
// integration, never stored next to this file or accepted through MCP/env/CLI.
import {createCipheriv,createDecipheriv,randomBytes} from 'node:crypto';
import {lstatSync,openSync,readFileSync,writeFileSync,fsyncSync,closeSync,renameSync,unlinkSync} from 'node:fs';
import {join} from 'node:path';
import {SafeError} from './ais.mjs';
const bad=()=>{throw new SafeError('ENCRYPTED_STORE');};
export class EncryptedStore {
  constructor(directory,key) {
    if(process.platform==='win32') bad(); // No pretend POSIX mode -> Windows ACL guarantee.
    if(!Buffer.isBuffer(key)||key.length!==32)bad();
    this.key=Buffer.from(key);this.dir=directory;this.closed=true;
    const d=lstatSync(directory);
    if(!d.isDirectory()||d.isSymbolicLink()||d.uid!==process.getuid()||(d.mode&0o077)!==0)bad();
    this.path=join(directory,'state.aesgcm');this.lock=join(directory,'owner.lock');
    try{const fd=openSync(this.lock,'wx',0o600);closeSync(fd);this.closed=false;}catch{bad();}
    // A crashed process leaves its lock. Never steal it or reset quota automatically.
  }
  check() {if(this.closed)bad();}
  read() {
    this.check();
    try {
      const stat=lstatSync(this.path);
      if(!stat.isFile()||stat.isSymbolicLink()||stat.uid!==process.getuid()||(stat.mode&0o077)!==0||stat.size>262144)bad();
      const raw=readFileSync(this.path);
      if(raw.length<33||raw[0]!==1)bad();
      const decipher=createDecipheriv('aes-256-gcm',this.key,raw.subarray(1,13));
      decipher.setAAD(Buffer.from('bankmcp-minimal/state/v1'));
      decipher.setAuthTag(raw.subarray(13,29));
      return JSON.parse(Buffer.concat([decipher.update(raw.subarray(29)),decipher.final()]).toString('utf8'));
    }catch{bad();}
  }
  write(state) {
    this.check();let fd;let temp;
    try {
      const plain=Buffer.from(JSON.stringify(state));if(plain.length>200000)bad();
      const iv=randomBytes(12);const cipher=createCipheriv('aes-256-gcm',this.key,iv);
      cipher.setAAD(Buffer.from('bankmcp-minimal/state/v1'));
      const encrypted=Buffer.concat([cipher.update(plain),cipher.final()]);plain.fill(0);
      const raw=Buffer.concat([Buffer.from([1]),iv,cipher.getAuthTag(),encrypted]);
      temp=join(this.dir,`pending-${randomBytes(16).toString('hex')}`);
      fd=openSync(temp,'wx',0o600);writeFileSync(fd,raw);fsyncSync(fd);closeSync(fd);fd=undefined;
      renameSync(temp,this.path);temp=undefined;
      fd=openSync(this.dir,'r');fsyncSync(fd);closeSync(fd);fd=undefined;
    }catch{if(fd!==undefined)try{closeSync(fd);}catch{};if(temp)try{unlinkSync(temp);}catch{};bad();}
  }
  close(){if(!this.closed){this.closed=true;this.key.fill(0);unlinkSync(this.lock);}}
}
