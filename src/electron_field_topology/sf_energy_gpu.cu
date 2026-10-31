/* Apache-2.0. Float64 CUDA port of sf_energy.c:sf_cell.
 * Eight disjoint cell colours avoid gradient atomics. Same Gauss rule,
 * normalization adjoint, nonsingular-cell guards and corner order.
 * EFT_HOST_CHECK executes this exact cell function serially for CPU tests;
 * it is never presented as a GPU benchmark.
 */
#ifdef EFT_HOST_CHECK
#include <math.h>
#define EFT_DEVICE
#else
#define EFT_DEVICE __device__ __forceinline__
#endif
EFT_DEVICE void eft_cell(int n,double h,const double *u,double *grad,double *metrics,
                        const double *shapes,const double *ders,int color,long tid){
    const long m=(n-1)/2;
    int x=2*(tid/(m*m))+((color>>2)&1);
    int y=2*((tid/m)%m)+((color>>1)&1);
    int z=2*(tid%m)+(color&1);
    const double (*shape)[8]=(const double (*)[8])shapes;
    const double (*der)[8][3]=(const double (*)[8][3])ders;
    double e2=0.,e4=0.,minimum=1.,cone=1.;
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

    long cell=((long)x*(n-1)+y)*(n-1)+z;
    long count=(long)(n-1)*(n-1)*(n-1);
    metrics[cell]=e2;metrics[count+cell]=e4;
    metrics[2*count+cell]=minimum;metrics[3*count+cell]=cone;
}
#ifdef EFT_HOST_CHECK
extern "C" void sf_cell_color_host(int n,double h,const double *u,double *grad,double *metrics,
                                    const double *shapes,const double *ders,int color){
    long m=(n-1)/2;
    for(long tid=0;tid<m*m*m;tid++)eft_cell(n,h,u,grad,metrics,shapes,ders,color,tid);
}
#else
extern "C" __global__ void sf_cell_color(int n,double h,const double *u,double *grad,double *metrics,
                                        const double *shapes,const double *ders,int color){
    long tid=(long)blockIdx.x*blockDim.x+threadIdx.x;
    long m=(n-1)/2;
    if(tid<m*m*m)eft_cell(n,h,u,grad,metrics,shapes,ders,color,tid);
}
#endif
