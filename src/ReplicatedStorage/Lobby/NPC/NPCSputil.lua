-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:37 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_5 = require(game.ReplicatedStorage.Lobby.Menus.WebNPCShopUI)
return {
    ["new"] = function(_, p6, p_u_7) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_5 ]]
        return v_u_4:new(p6, p_u_7, v_u_3.NPC.NPC_sputil, "Friendly Alien", "Leave a NPC", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupWebNPCShop, true, function(p_u_8, _, p9) --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_7 ]]
            local v_u_10 = p_u_8:load_anim(p9, v_u_1.ANIM_OLDSCHOOLSHUFFLE)
            p_u_7._update_enqueue_fn:enqueue_function(function() --[[ Line: 22 ]]
                --[[ Upvalues: (copy 1): p_u_8, (copy 2): v_u_10 ]]
                p_u_8:play_anim(v_u_10)
            end, 45)
        end, function(p11, p12, p13) --[[ Line: 26 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_5 ]]
            p11._sfx_manager:play_sfx(v_u_2.SFX_MENU_OPEN)
            p13:push_menu(v_u_5:new(p11, p12, p13))
        end);
    end
};
