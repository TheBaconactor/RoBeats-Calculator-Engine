-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPVector)
local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPMultiDict)
require(game.ReplicatedStorage.LocalShared.SPImagePriority)
local s_ContentProvider_0 = game:GetService("ContentProvider")
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): s_ContentProvider_0, (copy 4): v_u_1 ]]
        local v4 = {
            ["cons"] = function(_) end
        }
        local v_u_5 = v_u_2:new():push_back_table_list({
            v_u_3.SFX_FEVERCHEER_1,
            v_u_3.SFX_STARTCHEER_1,
            v_u_3.SFX_COUNTDOWN_READY,
            v_u_3.SFX_COUNTDOWN_GO,
            v_u_3.SFX_MENU_CLOSE,
            v_u_3.SFX_MENU_OPEN,
            v_u_3.SFX_MENU_CLOSE_LONG,
            v_u_3.SFX_MENU_OPEN_LONG,
            v_u_3.SFX_DRUM_OKAY,
            v_u_3.SFX_MISS,
            v_u_3.SFX_TICK,
            v_u_3.SFX_ACQUIRE,
            v_u_3.SFX_BUTTONPRESS,
            v_u_3.SFX_HITFXG_DRUM_1,
            v_u_3.SFX_HITFXG_DRUM_2,
            v_u_3.SFX_ENDCHEER_1,
            v_u_3.SFX_HITFXG_TAMB_1,
            v_u_3.SFX_HITFXG_TAMB_2,
            v_u_3.SFX_HITFXG_INDHIHAT_1,
            v_u_3.SFX_HITFXG_INDHIHAT_2,
            v_u_3.SFX_HITFXG_INDHIHAT_3,
            v_u_3.SFX_HITFXG_HIHAT_1,
            v_u_3.SFX_HITFXG_HIHAT_2,
            v_u_3.SFX_HITFXG_HIHAT_3,
            v_u_3.SFX_HITFXG_CLAP_1,
            v_u_3.SFX_HITFXG_CLAP_2,
            v_u_3.SFX_HITFXG_JAZZHH_1,
            v_u_3.SFX_HITFXG_JAZZHH_2,
            v_u_3.SFX_HITFXG_JAZZHH_3,
            v_u_3.SFX_FANFARE,
            v_u_3.SFX_MENU_BUY
        })
        local l_Sound_0 = Instance.new("Sound", game:GetService("SoundService"))
        local v_u_6 = ""
        v4.update = function(_, p_u_7, _) --[[ Name: update ]] --[[ Line: 64 ]]
            --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_6, (copy 3): l_Sound_0, (ref 4): s_ContentProvider_0, (ref 5): v_u_1 ]]
            if v_u_5:count() ~= 0 then
                local v_u_8 = v_u_5:get(1)
                if v_u_6 ~= v_u_8 then
                    v_u_6 = v_u_8
                    l_Sound_0.SoundId = v_u_8
                    spawn(function() --[[ Line: 72 ]]
                        --[[ Upvalues: (ref 1): s_ContentProvider_0, (ref 2): l_Sound_0, (ref 3): v_u_5, (copy 4): p_u_7, (copy 5): v_u_8, (ref 6): v_u_1 ]]
                        s_ContentProvider_0:PreloadAsync({ l_Sound_0 })
                        v_u_5:pop_front()
                        p_u_7._sfx_manager:preload(v_u_8, 1, 0.5)
                        if v_u_5:count() == 0 then
                            v_u_1:puts("Sounds have preloaded")
                        end;
                    end)
                end;
            end;
        end;
        v4:cons()
        return v4;
    end
};
