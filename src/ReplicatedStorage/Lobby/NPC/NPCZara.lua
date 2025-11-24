-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:36 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.AnimationManager)
local v_u_2 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_4 = require(game.ReplicatedStorage.Lobby.NPC.NPCAsyncLoad)
local v_u_5 = require(game.ReplicatedStorage.Lobby.Menus.GearShopUI)
return {
    ["new"] = function(_, p6, p7) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3, (copy 3): v_u_1, (copy 4): v_u_5, (copy 5): v_u_2 ]]
        return v_u_4:new(p6, p7, v_u_3.NPC.NPC_Zara, "Zara", "Gear Shop", game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.DialoguePopupGearShop, true, function(p8, _, p9) --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            p8:play_anim((p8:load_anim(p9, v_u_1.ANIM_MARIE_TALK)))
        end, function(p10, p11, p12) --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_2 ]]
            p12:push_menu(v_u_5:new(p10, p11, p12))
            p10._sfx_manager:play_sfx(v_u_2.SFX_MENU_OPEN)
        end);
    end
};
