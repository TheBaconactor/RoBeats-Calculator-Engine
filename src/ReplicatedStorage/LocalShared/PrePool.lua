-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:00 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.Note)
local v_u_2 = require(game.ReplicatedStorage.Local.HeldNote)
local v_u_3 = require(game.ReplicatedStorage.Effects.TriggerNoteEffect_Adorn)
local v_u_4 = require(game.ReplicatedStorage.Effects.HoldingNoteEffect_Adorn)
local v_u_5 = require(game.ReplicatedStorage.Effects.NoteResultPopupEffectV2)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Local.NoteDecal.TriggerNoteEffectDecal)
local v_u_7 = require(game.ReplicatedStorage.Local.NoteDecal.NoteResultPopupEffectDecal)
return {
    ["prepool"] = function(_, p8) --[[ Name: prepool ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_6, (copy 5): v_u_5, (copy 6): v_u_7, (copy 7): v_u_4 ]]
        p8._sfx_manager:prepool()
        p8._adorn_pool:prepool()
        for _ = 1, 100 do
            v_u_1:prepool(p8)
        end;
        for _ = 1, 30 do
            v_u_2:prepool(p8)
        end;
        for _ = 1, 20 do
            v_u_3:prepool(p8)
            v_u_6:prepool(p8)
        end;
        for _ = 1, 20 do
            v_u_5:prepool(p8)
            v_u_7:prepool(p8)
        end;
        for _ = 1, 15 do
            v_u_4:prepool(p8)
        end;
    end
};
