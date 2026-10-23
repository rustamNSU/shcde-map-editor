// Offline ports of CrusaderDE.dll D86F0/DAA50/DE6A0/E49D0.
// Input arrays belong to the map document. No game process or DLL is loaded.
#include <stdint.h>
#include <vector>
#include <algorithm>

static constexpr uint32_t OBSTACLES = 0x4a5014b1;
static bool special(int type) {
    switch(type) {
    case 41: case 42: case 43: case 44: case 45: case 46: case 47:
    case 73: case 153: case 154: case 155: case 156: case 157: case 158:
    case 159: case 185: case 186: case 187: case 188: case 189: case 190: return true;
    default: return false;
    }
}
static bool corner_building(int type) {
    switch(type) {
    case 8: case 9: case 11: case 34: case 36: case 40: case 41: case 42:
    case 43: case 44: case 45: case 46: case 47: case 48: case 70: case 71:
    case 72: case 73: case 74: case 75: case 76: case 77: case 78: case 79:
    case 152: case 153: case 154: case 155: case 156: case 157: case 158:
    case 159: case 160: case 183: case 184: case 185: case 186: case 187:
    case 188: case 189: case 190: case 225: case 226: case 227: case 228:
    case 229: case 230: case 231: case 232: case 233: case 235: case 236:
    case 237: case 238: case 239: return true;
    default: return false;
    }
}
static int building_height(int type) {
    switch(type) {
    case 40:return 64; case 41:return 92; case 42:return 190;
    case 45:case 46:return 128; case 69:return 118;
    case 74:return 296; case 75:return 148; case 76:return 180;
    case 77:case 78:return 192; default:return 0;
    }
}

extern "C" __declspec(dllexport) int label_components(
    int count, const uint32_t* logic, const uint8_t* tree_pass,
    const int32_t* neighbors, const uint8_t* edges, uint16_t* components);

extern "C" __declspec(dllexport) int rebuild_navigation(
    int count, const uint32_t* logic, const uint8_t* height, const int8_t* damage,
    const uint16_t* slots, const int16_t* types, const uint8_t* tree_pass,
    const int32_t* neighbors, uint8_t* edges, uint16_t* components, int cleanup) {
    std::vector<int> corners;
    for (int i=0;i<count;i++) {
        uint32_t f=logic[i];
        const int type=types[i];
        const bool sp=slots[i]!=0 && special(type);
        int low=int(height[i])-16, high=int(height[i])+16;
        if(f&0x10000000) { low+=building_height(type);high+=building_height(type); }
        bool wall=false, stairs=false, elevated=false, corner_mode=false;
        int source_class=0;
        edges[i]=0;
        if(!(f&0x800000)) {
            if(!(f&0x10000000)) {
                if((f&0x402)==0x402) continue;
                if(!(f&2) && !(f&0x200000)) {
                    if(f&0x800) stairs=true;
                    else if(f&0x400000) continue;
                    else if(!(f&0x100)) {
                        if(f&OBSTACLES) {
                            if(!(f&0x1000) || !tree_pass[i]) continue;
                        } else corner_mode=true;
                    } else { wall=true;source_class=slots[i]!=0?2:0; }
                } else corner_mode=true;
            } else { source_class=1;elevated=true; }
        }
        uint8_t result=0, blocked=0;
        uint32_t nf[8];
        for(int d=0;d<8;d++) {
            const uint8_t bit=uint8_t(1u<<d);
            const int j=neighbors[i*8+d];
            nf[d]=j<0 ? 0x10 : logic[j];
            if(j<0) {blocked|=bit;continue;}
            const uint32_t g=nf[d];
            bool common=false;
            if(g&0x200000) common=true;
            else if(g&0x800) common=source_class!=1 && damage[j]<21;
            else if(g&2) common=!elevated && (!(g&0x400) || slots[j]==0) && !sp;
            else if(g&0x400) { if(corner_building(types[j])) blocked|=bit; }
            else if(g&0x10000000) {blocked|=bit;common=true;}
            else if(g&0x400000) blocked|=bit;
            else if(g&0x100) {blocked|=bit;common=true;}
            else if(g&0x30) blocked|=bit;
            else if(!(g&OBSTACLES) || ((g&0x1000) && tree_pass[j])) common=true;
            if(!common) continue;
            bool pass=false;
            if(g&0x10000000) pass=elevated || (wall && damage[i]<=20);
            else if((g&0x100) && source_class!=0) pass=damage[j]<=20;
            else if((wall || stairs) && (g&0x100) && slots[j]!=0) pass=damage[i]<=20;
            else pass=height[j]>=low && height[j]<=high;
            if(pass) result|=bit;
        }
        bool queued=false;
        const int card_a[4]={0,0,4,4}, card_b[4]={2,6,2,6}, diagonal[4]={1,7,3,5};
        for(int c=0;c<4;c++) {
            int a=card_a[c],b=card_b[c],d=diagonal[c];
            if(!corner_mode) {
                if((nf[a]&0x10000100) && (nf[b]&0x10000100) &&
                   !(nf[d]&0x10000102) && !(nf[a]&0x800) && !(nf[b]&0x800))
                    result&=uint8_t(~(1<<d));
            } else if(!(result&(1<<a)) && (blocked&(1<<a)) &&
                      !(result&(1<<b)) && (blocked&(1<<b))) {
                result&=uint8_t(~(1<<d));queued=true;
            }
        }
        edges[i]=result;
        if(queued) corners.push_back(i);
    }
    // DE6A0 visits queued cells in ascending tile order and updates reverse edges.
    if(cleanup) for(int i:corners) {
        const uint8_t e=edges[i];
        for(int d=0;d<8;d++) {
            int j=neighbors[i*8+d];
            if(j<0 || (logic[j]&0x30)) continue;
            if((logic[j]&OBSTACLES) && (!(logic[j]&0x1000) || !tree_pass[j])) continue;
            const uint8_t opposite=uint8_t(1u<<((d+4)%8));
            if(e&(1<<d)) edges[j]|=opposite;
            else edges[j]&=uint8_t(~opposite);
        }
    }
    return label_components(count,logic,tree_pass,neighbors,edges,components);
}

extern "C" __declspec(dllexport) int label_components(
    int count, const uint32_t* logic, const uint8_t* tree_pass,
    const int32_t* neighbors, const uint8_t* edges, uint16_t* components) {
    std::fill(components,components+count,0);
    std::vector<int> queue(count);
    int component=0;
    const int order[8]={6,2,0,7,1,4,5,3};
    for(int seed=0;seed<count && component<999;seed++) {
        if(components[seed] || ((logic[seed]&OBSTACLES) &&
           (!(logic[seed]&0x1000) || !tree_pass[seed]))) continue;
        ++component;
        int head=0,tail=1;queue[0]=seed;components[seed]=uint16_t(component);
        while(head<tail) {
            int i=queue[head++];
            for(int d:order) {
                if(!(edges[i]&(1<<d))) continue;
                int j=neighbors[i*8+d];
                if(j<0 || components[j]) continue;
                components[j]=uint16_t(component);queue[tail++]=j;
            }
        }
    }
    return component;
}
