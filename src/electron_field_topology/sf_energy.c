/* Apache-2.0. Optional accelerator for the explicitly discrete static energy.
 * Forward D; exact transpose with constant exterior values.
 * Python's independent NumPy implementation is the validation reference. */
#include <math.h>
#include <stddef.h>
#include <string.h>

void sf_energy(int n, double h, const double *u, double *flux, double *grad,
               double *parts) {
    const long N=(long)n*n*n, stride[3]={(long)n*n,n,1};
    double e2=0.,e4=0.;
    #pragma omp parallel for reduction(+:e2,e4) schedule(static)
    for(long s=0;s<N;s++) {
        int coord[3]={(int)(s/(n*n)),(int)((s/n)%n),(int)(s%n)};
        double d[3][3]={{0}}, p[3][3]={{0}}, norm[3]={0};
        for(int i=0;i<3;i++) {
            int c=coord[i]+1;
            for(int a=0;a<3;a++)
                d[i][a]=((c<n?u[3*(s+stride[i])+a]:(a==2?1.:0.))-u[3*s+a])/h;
        }
        for(int i=0;i<3;i++) for(int a=0;a<3;a++) {
            norm[i]+=d[i][a]*d[i][a]; p[i][a]=2*d[i][a];
        }
        e2+=norm[0]+norm[1]+norm[2];
        for(int i=0;i<3;i++) for(int j=i+1;j<3;j++) {
            double dot=0.;for(int a=0;a<3;a++)dot+=d[i][a]*d[j][a];
            /* Cross products avoid cancellation for parallel derivatives. */
            for(int a=0;a<3;a++) {
                double cross=d[i][(a+1)%3]*d[j][(a+2)%3]-d[i][(a+2)%3]*d[j][(a+1)%3];
                e4+=cross*cross;
                p[i][a]+=2*(norm[j]*d[i][a]-dot*d[j][a]);
                p[j][a]+=2*(norm[i]*d[j][a]-dot*d[i][a]);
            }
        }
        for(int i=0;i<3;i++)for(int a=0;a<3;a++)flux[9*s+3*i+a]=p[i][a];
    }
    #pragma omp parallel for schedule(static)
    for(long s=0;s<N;s++) {
        int coord[3]={(int)(s/(n*n)),(int)((s/n)%n),(int)(s%n)};
        for(int a=0;a<3;a++) {
            double g=0.;
            for(int i=0;i<3;i++) {
                g-=flux[9*s+3*i+a]/h;
                if(coord[i]>0)g+=flux[9*(s-stride[i])+3*i+a]/h;
            }
            grad[3*s+a]=g;
        }
    }
    parts[0]=e2;parts[1]=e4;parts[2]=1.;parts[3]=1.;
}

/* Normalised trilinear field, 2x2x2 Gauss rule on each cell. Gradient is
 * differentiated through the interpolation and unit normalisation. */
void sf_cell(int n,double h,const double *u,double *unused,double *grad,double *parts){
    long N=(long)n*n*n;memset(grad,0,3*N*sizeof(double));
    double shape[8][8],der[8][8][3],gauss[2]={.5-.5/sqrt(3.),.5+.5/sqrt(3.)};
    for(int q=0;q<8;q++)for(int a=0;a<8;a++){
        double f[3],df[3];
        for(int i=0;i<3;i++){
            int bit=(a>>(2-i))&1;double x=gauss[(q>>(2-i))&1];
            f[i]=bit?x:1-x;df[i]=(bit?1.:-1.)/h;
        }
        shape[q][a]=f[0]*f[1]*f[2];
        for(int i=0;i<3;i++)der[q][a][i]=df[i]*f[(i+1)%3]*f[(i+2)%3];
    }
    double e2=0.,e4=0.,minimum=1.,cone=1.;
    for(int color=0;color<8;color++){
        #pragma omp parallel for reduction(+:e2,e4) reduction(min:minimum,cone) schedule(static)
        for(int x=(color>>2)&1;x<n-1;x+=2)for(int y=(color>>1)&1;y<n-1;y+=2)for(int z=color&1;z<n-1;z+=2){
            long ids[8];double local[8][3]={{0}};
            for(int a=0;a<8;a++)ids[a]=((long)(x+((a>>2)&1))*n+y+((a>>1)&1))*n+z+(a&1);
            double centre[3]={0},length=0.;
            for(int a=0;a<8;a++)for(int j=0;j<3;j++)centre[j]+=u[3*ids[a]+j];
            for(int j=0;j<3;j++)length+=centre[j]*centre[j];length=sqrt(length);
            for(int a=0;a<8;a++){
                double dot=0.;for(int j=0;j<3;j++)dot+=u[3*ids[a]+j]*centre[j]/fmax(length,1e-15);
                if(dot<cone)cone=dot;
            }
            for(int q=0;q<8;q++){
                double v[3]={0},dv[3][3]={{0}},nn[3],r=0.,c[3]={0},d[3][3],p[3][3],norm[3]={0},gv[3]={0},pp[3][3];
                for(int a=0;a<8;a++)for(int j=0;j<3;j++){
                    v[j]+=shape[q][a]*u[3*ids[a]+j];
                    for(int i=0;i<3;i++)dv[i][j]+=der[q][a][i]*u[3*ids[a]+j];
                }
                for(int j=0;j<3;j++)r+=v[j]*v[j];r=sqrt(r);
                if(r<minimum)minimum=r;
                if(r<1e-12)r=1e-12; /* energy is rejected below, never accepted with this floor */
                for(int j=0;j<3;j++)nn[j]=v[j]/r;
                for(int i=0;i<3;i++){
                    for(int j=0;j<3;j++)c[i]+=nn[j]*dv[i][j];
                    for(int j=0;j<3;j++){d[i][j]=(dv[i][j]-nn[j]*c[i])/r;norm[i]+=d[i][j]*d[i][j];p[i][j]=2*d[i][j];}
                }
                e2+=(norm[0]+norm[1]+norm[2])/8;
                for(int i=0;i<3;i++)for(int j=i+1;j<3;j++){
                    double dot=0.;for(int a=0;a<3;a++)dot+=d[i][a]*d[j][a];
                    for(int a=0;a<3;a++){
                        double cr=d[i][(a+1)%3]*d[j][(a+2)%3]-d[i][(a+2)%3]*d[j][(a+1)%3];e4+=cr*cr/8;
                        p[i][a]+=2*(norm[j]*d[i][a]-dot*d[j][a]);p[j][a]+=2*(norm[i]*d[j][a]-dot*d[i][a]);
                    }
                }
                for(int i=0;i<3;i++){
                    double ndotp=0.,pdotd=0.;for(int j=0;j<3;j++){ndotp+=nn[j]*p[i][j];pdotd+=p[i][j]*d[i][j];}
                    for(int j=0;j<3;j++){
                        pp[i][j]=(p[i][j]-nn[j]*ndotp)/r;
                        gv[j]-=nn[j]*pdotd/r+c[i]*pp[i][j]/r+ndotp*d[i][j]/r;
                    }
                }
                for(int a=0;a<8;a++)for(int j=0;j<3;j++){
                    local[a][j]+=shape[q][a]*gv[j]/8;
                    for(int i=0;i<3;i++)local[a][j]+=der[q][a][i]*pp[i][j]/8;
                }
            }
            for(int a=0;a<8;a++)for(int j=0;j<3;j++)grad[3*ids[a]+j]+=local[a][j];
        }
    }
    parts[0]=e2;parts[1]=e4;parts[2]=minimum;parts[3]=cone;
}
