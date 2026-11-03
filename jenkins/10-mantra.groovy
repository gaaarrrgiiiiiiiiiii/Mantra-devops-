import jenkins.model.Jenkins
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import com.cloudbees.plugins.credentials.CredentialsScope
import com.cloudbees.plugins.credentials.SystemCredentialsProvider
import com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import hudson.plugins.git.GitSCM
import hudson.plugins.git.UserRemoteConfig
import hudson.plugins.git.BranchSpec
import hudson.triggers.SCMTrigger

def jenkins = Jenkins.get()
if (!(jenkins.securityRealm instanceof HudsonPrivateSecurityRealm)) {
    def realm = new HudsonPrivateSecurityRealm(false)
    realm.createAccount('mantra-admin', new File('/var/lib/jenkins/secrets/mantra-admin-password').text.trim())
    jenkins.setSecurityRealm(realm)
}
def authorization = new FullControlOnceLoggedInAuthorizationStrategy()
authorization.setAllowAnonymousRead(false)
jenkins.setAuthorizationStrategy(authorization)
jenkins.setSlaveAgentPort(-1)
jenkins.setNumExecutors(1)

def credentials = SystemCredentialsProvider.getInstance().getCredentials()
if (!credentials.any { it.id == 'mantra-ec2-ssh' }) {
    credentials.add(new BasicSSHUserPrivateKey(
        CredentialsScope.GLOBAL, 'mantra-ec2-ssh', 'ubuntu',
        new BasicSSHUserPrivateKey.DirectEntryPrivateKeySource(new File('/var/lib/jenkins/.ssh/id_ed25519').text),
        '', 'Dedicated Jenkins deployment key for the Mantra host'
    ))
    SystemCredentialsProvider.getInstance().save()
}

if (jenkins.getItem('Mantra') == null) {
    def job = jenkins.createProject(WorkflowJob, 'Mantra')
    def scm = new GitSCM(
        [new UserRemoteConfig('https://github.com/gaaarrrgiiiiiiiiiii/Mantra-devops-.git', null, null, null)],
        [new BranchSpec('*/main')], false, [], null, null, []
    )
    job.setDefinition(new CpsScmFlowDefinition(scm, 'Jenkinsfile'))
    job.setDisabled(true)
    job.addTrigger(new SCMTrigger('H/5 * * * *'))
    job.setDescription('Mantra main branch. Enable after the verified platform changes are published. Private controller on EC2.')
    job.save()
}
jenkins.save()
