-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 5 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v2 = {}
        v2.get_requirements = function(p3, _) --[[ Name: get_requirements ]] --[[ Line: 8 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("SongRecipeBase >> (%s) must implement get_requirements", p3:get_name())
        end;
        v2.get_song = function(p4) --[[ Name: get_song ]] --[[ Line: 12 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:errf("SongRecipeBase >> (%s) must implement get_song", p4:get_name())
        end;
        return v2;
    end
};
