-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Effects.EffectSystem)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Local.DebugOut)
local v41 = {
    ["EffectObject"] = {},
    ["new"] = function(_, p5) --[[ Name: new ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_2 ]]
        local v6 = v_u_1:EffectBase()
        v6._effect_obj = p5
        v6._anim_t = 0
        v6._position = v_u_4.new(0, 0, 0)
        v6._r = 0
        v6._vr = 0
        v6._scale = v_u_3:new(1, 1)
        v6._alpha = v_u_3:new(1, 1)
        v6._velocity = v_u_4:new(0, 0, 0)
        v6._acceleration = v_u_4:new(0, 0, 0)
        v6._tick_incr = v_u_2:SecondsToTick(0.5)
        v6.cons = function(p7) --[[ Name: cons ]] --[[ Line: 39 ]]
            p7:update_visual()
        end;
        v6.set_duration_seconds = function(p8, p9) --[[ Name: set_duration_seconds ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            p8._tick_incr = v_u_2:SecondsToTick(p9)
            return p8;
        end;
        v6.set_position = function(p10, p11, p12, p13) --[[ Name: set_position ]] --[[ Line: 47 ]]
            p10._position:set(p11, p12, p13)
            return p10;
        end;
        v6.set_rotation = function(p14, p15) --[[ Name: set_rotation ]] --[[ Line: 51 ]]
            p14._r = p15
            return p14;
        end;
        v6.set_vrotation = function(p16, p17) --[[ Name: set_vrotation ]] --[[ Line: 55 ]]
            p16._vr = p17
            return p16;
        end;
        v6.set_scale = function(p18, p19, p20) --[[ Name: set_scale ]] --[[ Line: 59 ]]
            p18._scale:set_min_max(p19, p20)
            return p18;
        end;
        v6.set_alpha = function(p21, p22, p23) --[[ Name: set_alpha ]] --[[ Line: 63 ]]
            p21._alpha:set_min_max(p22, p23)
            return p21;
        end;
        v6.set_velocity = function(p24, p25, p26, p27) --[[ Name: set_velocity ]] --[[ Line: 67 ]]
            p24._velocity:set(p25, p26, p27)
            return p24;
        end;
        v6.set_acceleration = function(p28, p29, p30, p31) --[[ Name: set_acceleration ]] --[[ Line: 71 ]]
            p28._acceleration:set(p29, p30, p31)
            return p28;
        end;
        v6.update = function(p32, p33, _) --[[ Name: update ]] --[[ Line: 76 ]]
            p32._anim_t = p32._anim_t + p32._tick_incr * p33
            p32._position:add_scaled(p32._velocity, p33)
            p32._velocity:add_scaled(p32._acceleration, p33)
            p32._r = p32._r + p32._vr * p33
            p32:update_visual()
        end;
        v6.update_visual = function(p34) --[[ Name: update_visual ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            p34._effect_obj:set_position(p34._position._x, p34._position._y, p34._position._z)
            p34._effect_obj:set_alpha(v_u_2:Lerp(p34._alpha._min, p34._alpha._max, p34._anim_t))
            p34._effect_obj:set_rotation(p34._r)
            p34._effect_obj:set_scale(v_u_2:Lerp(p34._scale._min, p34._scale._max, p34._anim_t))
        end;
        v6.add_to_parent = function(p35, p36, p37) --[[ Name: add_to_parent ]] --[[ Line: 111 ]]
            p35._effect_obj:add_to_parent(p36, p37)
        end;
        v6.should_remove = function(p38, _) --[[ Name: should_remove ]] --[[ Line: 114 ]]
            return p38._anim_t >= 1;
        end;
        v6.do_remove = function(p39, p40) --[[ Name: do_remove ]] --[[ Line: 117 ]]
            p39._effect_obj:do_remove(p40)
            p39._effect_obj = nil
        end;
        v6:cons()
        return v6;
    end
}
v41.EffectObject.new = function(_) --[[ Name: new ]] --[[ Line: 11 ]]
    return {
        ["set_position"] = function(_, _, _, _) end,
        ["set_alpha"] = function(_, _) end,
        ["set_rotation"] = function(_, _) end,
        ["set_scale"] = function(_, _) end,
        ["add_to_parent"] = function(_, _, _) end,
        ["do_remove"] = function(_, _) end
    };
end;
return v41;
