# Zubbi Demo on Kubernetes

Prerequisites: [Kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
installed

---

**NOTE:**
This guide is based on
[How to Set Up an Nginx Ingress with Cert-Manager on DigitalOcean Kubernetes](https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nginx-ingress-with-cert-manager-on-digitalocean-kubernetes).
For more detailed information take a look at the original guide.

---

To set up the zubbi demo on a Kubernetes cluster, follow these steps:

1. Set the `KUBECONFIG` environment variable to point to your configuration
   file, e.g.:
   ```shell
   $ export KUBECONFIG=~/.kube/zubbi-k8s-config.yaml
   ```

2. Deploy following files in the `k8s` directory via `kubectl` to create the
   deployments for Elasticsearch and Zubbi:
   ```shell
   $ kubectl apply -f k8s/elasticsearch.yaml
   $ kubectl apply -f k8s/zubbi.yaml
   ```

3. If you want Zubbi to be reachable from the outside, you need to set up a
   Kubernetes Nginx Ingress Controller, like so:
   ```shell
   $ kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/mandatory.yaml
   $ kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/provider/cloud-generic.yaml
   ```
   
   Afterwards, you need to define an Ingress for zubbi:
   ```shell
   $ kubectl apply -f k8s/zubbi-ingress.yaml
   ```
   
   If everything is set up, you should be able to see Zubbi running on http://zubbi.example.de.
