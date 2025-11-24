-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = v_u_1:SPUIObjectBase()
        local v_u_3 = false
        v2.set_sptmp_debug = function(_, p4) --[[ Name: set_sptmp_debug ]] --[[ Line: 14 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3 = p4
        end;
        v2.is_sptmp_debug = function(_) --[[ Name: is_sptmp_debug ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            return v_u_3;
        end;
        v2.set_selected = function(_, _, _) end;
        v2.trigger_element = function(_, _) end;
        v2.update = function(_, _, _) end;
        v2.behaviour_update = function(_, _, _) end;
        v2.get_selected = function(_) --[[ Name: get_selected ]] --[[ Line: 21 ]]
            return false;
        end;
        v2.trigger_element = function(_, _) end;
        v2.is_selectable = function(_) --[[ Name: is_selectable ]] --[[ Line: 24 ]]
            return true;
        end;
        v2.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 27 ]]
            return Vector2.new();
        end;
        v2.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 28 ]]
            return Vector2.new();
        end;
        v2.set_size = function(_, _) end;
        v2.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 30 ]]
            return Vector3.new();
        end;
        v2.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 31 ]]
            return nil;
        end;
        return v2;
    end
};
