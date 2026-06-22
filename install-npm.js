const https = require('https');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const nodeDir = process.env.LOCALAPPDATA + '\\node';
const npmVersion = '10.8.1';
const npmUrl = `https://registry.npmjs.org/npm/-/npm-${npmVersion}.tgz`;
const tgzPath = path.join(nodeDir, 'npm.tgz');
const extractDir = path.join(nodeDir, 'node_modules');
const npmPackageDir = path.join(extractDir, 'package');
const npmDir = path.join(extractDir, 'npm');
const npmCmdPath = path.join(path.dirname(process.argv[1]), 'npm.cmd');

console.log(`Installing npm ${npmVersion}...`);

if (!fs.existsSync(extractDir)) {
    fs.mkdirSync(extractDir, { recursive: true });
}

const file = fs.createWriteStream(tgzPath);
https.get(npmUrl, (response) => {
    response.pipe(file);
    file.on('finish', () => {
        file.close(() => {
            console.log('Download complete. Extracting...');
            
            try {
                execSync(`tar -xzf "${tgzPath}" -C "${extractDir}"`, { stdio: 'inherit' });
                fs.unlinkSync(tgzPath);
                
                if (fs.existsSync(npmDir)) {
                    execSync(`rmdir /s /q "${npmDir}"`, { stdio: 'ignore' });
                }
                
                fs.renameSync(npmPackageDir, npmDir);
                
                const npmCmdContent = `@echo off
setlocal
set "NODE_EXE=${nodeDir}\\node.exe"
set "NPM_CLI=${npmDir}\\bin\\npm-cli.js"
"%NODE_EXE%" "%NPM_CLI%" %*
endlocal`;
                fs.writeFileSync(npmCmdPath, npmCmdContent);
                
                console.log('npm installed successfully!');
                process.exit(0);
            } catch (err) {
                console.error('Error installing npm:', err.message);
                process.exit(1);
            }
        });
    });
}).on('error', (err) => {
    console.error('Error downloading npm:', err.message);
    process.exit(1);
});
